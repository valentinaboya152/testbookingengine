from django.db.models import F, Q, Count, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpRequest, HttpResponse
from typing import Dict, Any
from django.views import View
from .models import Room, Booking
from .forms import *
from .form_dates import Ymd
from django.views.decorators.csrf import ensure_csrf_cookie
from .reservation_code import generate
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


class BookingSearchView(View):
    # renders search results for bookingings
    def get(self, request):
        query = request.GET.dict()
        if (not "filter" in query):
            return redirect("/")
        bookings = (Booking.objects
                    .filter(Q(code__icontains=query['filter']) | Q(customer__name__icontains=query['filter']))
                    .order_by("-created"))
        room_search_form = RoomSearchForm()
        context = {
            'bookings': bookings,
            'form': room_search_form,
            'filter': True
        }
        return render(request, "home.html", context)


class RoomSearchView(View):
    # renders the search form
    def get(self, request):
        room_search_form = RoomSearchForm()
        context = {
            'form': room_search_form
        }

        return render(request, "booking_search_form.html", context)

    # renders the search results of available rooms by date and guests
    def post(self, request):
        query = request.POST.dict()
        # calculate number of days in the hotel
        checkin = Ymd.Ymd(query['checkin'])
        checkout = Ymd.Ymd(query['checkout'])
        total_days = checkout - checkin
        # get available rooms and total according to dates and guests
        filters = {
            'room_type__max_guests__gte': query['guests']
        }
        exclude = {
            'booking__checkin__lte': query['checkout'],
            'booking__checkout__gte': query['checkin'],
            'booking__state__exact': "NEW"
        }
        rooms = (Room.objects
                 .filter(**filters)
                 .exclude(**exclude)
                 .annotate(total=total_days * F('room_type__price'))
                 .order_by("room_type__max_guests", "name")
                 )
        total_rooms = (Room.objects
                       .filter(**filters)
                       .values("room_type__name", "room_type")
                       .exclude(**exclude)
                       .annotate(total=Count('room_type'))
                       .order_by("room_type__max_guests"))
        # prepare context data for template
        data = {
            'total_days': total_days
        }
        # pass the actual url query to the template
        url_query = request.POST.urlencode()
        context = {
            "rooms": rooms,
            "total_rooms": total_rooms,
            "query": query,
            "url_query": url_query,
            "data": data
        }
        return render(request, "search.html", context)


class HomeView(View):
    # renders home page with all the bookingings order by date of creation
    def get(self, request):
        bookings = Booking.objects.all().order_by("-created")
        context = {
            'bookings': bookings
        }
        return render(request, "home.html", context)


class BookingView(View):
    @method_decorator(ensure_csrf_cookie)
    def post(self, request, pk):
        # check if customer form is ok
        customer_form = CustomerForm(request.POST, prefix="customer")
        if customer_form.is_valid():
            # save customer data
            customer = customer_form.save()
            # add the customer id to the booking form
            temp_POST = request.POST.copy()
            temp_POST.update({
                'booking-customer': customer.id,
                'booking-room': pk,
                'booking-code': generate.get()})
            # if ok, save booking data
            booking_form = BookingForm(temp_POST, prefix="booking")
            if booking_form.is_valid():
                booking_form.save()
        return redirect('/')

    def get(self, request, pk):
        # renders the form for booking confirmation.
        # It returns 2 forms, the one with the booking info is hidden
        # The second form is for the customer information

        query = request.GET.dict()
        room = Room.objects.get(id=pk)
        checkin = Ymd.Ymd(query['checkin'])
        checkout = Ymd.Ymd(query['checkout'])
        total_days = checkout - checkin
        total = total_days * room.room_type.price  # total amount to be paid
        query['total'] = total
        url_query = request.GET.urlencode()
        booking_form = BookingFormExcluded(prefix="booking", initial=query)
        customer_form = CustomerForm(prefix="customer")
        context = {
            "url_query": url_query,
            "room": room,
            "booking_form": booking_form,
            "customer_form": customer_form
        }
        return render(request, "booking.html", context)

class EditBookingDatesForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['checkin', 'checkout']
        widgets = {
            'checkin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), # date input
            'checkout': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), # date input
        }
    def clean(self):
        cleaned_data = super().clean()
        checkin = cleaned_data.get("checkin")
        checkout = cleaned_data.get("checkout")

        if checkin and checkout and checkout <= checkin:
            raise forms.ValidationError("La fecha de salida debe ser posterior a la fecha de entrada.")
        return cleaned_data    
class EditBookingDatesView(View):
    def get(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        form = EditBookingDatesForm(instance=booking) # edit booking dates form
        return render(request, 'edit_booking_dates.html', {'form': form, 'booking': booking}) # render edit booking dates form

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        form = EditBookingDatesForm(request.POST, instance=booking)
        if form.is_valid():
            # Check availability
            checkin = form.cleaned_data['checkin']
            checkout = form.cleaned_data['checkout']
            
            # Check if there are other bookings on the same dates for the same room
            conflicting_bookings = Booking.objects.filter(
                room=booking.room,
                checkin__lt=checkout,
                checkout__gt=checkin,
            ).exclude(pk=booking.pk) # Exclude the current booking

            if conflicting_bookings.exists():
                messages.error(request, "No hay disponibilidad para las fechas seleccionadas.")
            else:
                form.save()
                messages.success(request, "Las fechas de la reserva han sido actualizadas correctamente.")
                return redirect('home')
        
        return render(request, 'edit_booking_dates.html', {'form': form, 'booking': booking})

@csrf_exempt  # permite llamadas AJAX sin token CSRF si lo pruebas directamente
def check_booking_availability(request, pk):
    """
    Endpoint AJAX para validar disponibilidad de la habitación al cambiar fechas en el formulario.
    """
    if request.method == "POST":
        booking = get_object_or_404(Booking, pk=pk)
        checkin = request.POST.get('checkin')
        checkout = request.POST.get('checkout')

        if not checkin or not checkout:
            return JsonResponse({'available': False, 'error': 'Debes seleccionar ambas fechas.'})

        from datetime import datetime
        checkin_date = datetime.strptime(checkin, "%Y-%m-%d").date()
        checkout_date = datetime.strptime(checkout, "%Y-%m-%d").date()

        if checkout_date <= checkin_date:
            return JsonResponse({'available': False, 'error': 'La fecha de salida debe ser posterior a la de entrada.'})

        conflicting = Booking.objects.filter(
            room=booking.room,
            checkin__lt=checkout_date,
            checkout__gt=checkin_date
        ).exclude(pk=booking.pk)

        if conflicting.exists():
            return JsonResponse({'available': False, 'error': 'No hay disponibilidad para las fechas seleccionadas.'})
        else:
            return JsonResponse({'available': True})

        return JsonResponse({'available': False, 'error': 'Método no permitido.'})
class DeleteBookingView(View):
    # renders the booking deletion form
    def get(self, request, pk):
        booking = Booking.objects.get(id=pk)
        context = {
            'booking': booking
        }
        return render(request, "delete_booking.html", context)

    # deletes the booking
    def post(self, request, pk):
        Booking.objects.filter(id=pk).update(state="DEL")
        return redirect("/")


class EditBookingView(View):
    # renders the booking edition form
    def get(self, request, pk):
        booking = Booking.objects.get(id=pk)
        booking_form = BookingForm(prefix="booking", instance=booking)
        customer_form = CustomerForm(prefix="customer", instance=booking.customer)
        context = {
            'booking_form': booking_form,
            'customer_form': customer_form

        }
        return render(request, "edit_booking.html", context)

    # updates the customer form
    @method_decorator(ensure_csrf_cookie)
    def post(self, request, pk):
        booking = Booking.objects.get(id=pk)
        customer_form = CustomerForm(request.POST, prefix="customer", instance=booking.customer)
        if customer_form.is_valid():
            customer_form.save()
            return redirect("/")


class DashboardView(View):
    def get(self, request):
        from datetime import date, time, datetime
        today = date.today()

        # get bookings created today
        today_min = datetime.combine(today, time.min)
        today_max = datetime.combine(today, time.max)
        today_range = (today_min, today_max)
        new_bookings = (Booking.objects
                        .filter(created__range=today_range)
                        .values("id")
                        ).count()

        # get incoming guests
        incoming = (Booking.objects
                    .filter(checkin=today)
                    .exclude(state="DEL")
                    .values("id")
                    ).count()

        # get outcoming guests
        outcoming = (Booking.objects
                     .filter(checkout=today)
                     .exclude(state="DEL")
                     .values("id")
                     ).count()

        # get outcoming guests
        invoiced = (Booking.objects
                    .filter(created__range=today_range)
                    .exclude(state="DEL")
                    .aggregate(Sum('total'))
                    )
         # Calculate occupancy rate
        total_rooms = Room.objects.count()
        confirmed_bookings = Booking.objects.filter(
            Q(checkin__lte=today) &  # Check-in es hoy o antes
            Q(checkout__gt=today) &   # Check-out es después de hoy
            ~Q(state="DEL")           # No incluir reservas eliminadas
        ).count()

        occupancy_rate = (confirmed_bookings / total_rooms * 100) if total_rooms > 0 else 0

        # preparing context data
        dashboard = {
            'new_bookings': new_bookings,
            'incoming_guests': incoming,
            'outcoming_guests': outcoming,
            'invoiced': invoiced,
            'occupancy_rate': round(occupancy_rate, 2),  # Redondear a 2 decimales
            'total_rooms': total_rooms,
            'occupied_rooms': confirmed_bookings
        }

        context = {
            'dashboard': dashboard
        }
        return render(request, "dashboard.html", context)


class RoomDetailsView(View):
    def get(self, request, pk):
        # renders room details
        room = Room.objects.get(id=pk)
        bookings = room.booking_set.all()
        context = {
            'room': room,
            'bookings': bookings}
        print(context)
        return render(request, "room_detail.html", context)


class RoomsView(View):
    """View responsible for listing rooms and allowing dynamic filtering by name.
    It supports:
      - Normal requests (renders HTML template with complete or filtered list).
      - AJAX requests (returns JSON with filtered rooms in real-time).
    """
    def get(self, request: HttpRequest) -> HttpResponse:
        # 1. Get the search parameter 'q' from the query string and normalize it.
        query = request.GET.get("q", "").strip()

        # 2. Build the base queryset: select the fields to be displayed.
        rooms = Room.objects.all().values("id", "name", "room_type__name")

        # 3. Apply the filter if the user provided a search query.
        if query:
            rooms = rooms.filter(name__icontains=query)  # name__icontains -> contains the substring without differentiating uppercase/lowercase

        # 4. Order results by name.
        rooms = rooms.order_by("name")

        # 5. If the request is AJAX, return JSON with the filtered list of rooms.
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            rooms_list = list(rooms)
            return JsonResponse({"rooms": rooms_list})

        # 6. For normal requests, render the template and pass the context.
        context: Dict[str, Any] = {
            "rooms": rooms,  # You can iterate over rooms in the template: for r in rooms
            "query": query,
        }
        return render(request, "rooms.html", context)
