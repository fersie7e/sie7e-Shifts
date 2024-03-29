from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse
from django.template.loader import render_to_string


from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

from .models import Venue, Shift, Employee, Provider, Service, Invoice, Fee, Performance
from .forms import ShiftForm
import calendar
import datetime

from django.views.generic import View

from rest_framework.views import APIView
from rest_framework.response import Response

# Constants declaration
YEARS_CHOICE = []

for year in range(2023, datetime.datetime.now().year + 2):
    YEARS_CHOICE.append(year)

MONTHS = {	'1':'January',
		'2':'February',
		'3':'March',
		'4':'April',
		'5':'May',
		'6':'June',
		'7':'July',
		'8':'August',
		'9':'September',
		'10':'October',
		'11':'November',
		'12':'December'		}

DAYSLONG = dict(enumerate(calendar.day_name))
DAYS = []

for number,day in DAYSLONG.items():
    DAYS.append(day[0:2])

CURRENT_MONTH = datetime.datetime.now().month
CURRENT_YEAR = datetime.datetime.now().year
TODAY = datetime.date.today()

# End of constant declaration

# Functions
def parseDate(date):
    """Converts a string 'yyyy/mm/dd' into date format

    Args:
        date (str): date to convert

    Returns:
        Date: Value with Date format
    """

    year = int(date[0:4])
    month = int(date[5:7])
    day = int(date[8:10])
    date_formated = datetime.date(year, month, day)
    return date_formated


def get_venues_allowed(user):
    """Get the venues that the user who is logged is allowed to manage

    Args:
        user (User): Instance of the user that logged into the app

    Returns:
        List: List with all the venues that a specific user can manage
    """

    venues = Venue.objects.all()
    venues_allowed = []
    for venue in venues:
        if user in venue.users.all():
            venues_allowed.append(venue)
    return venues_allowed


def get_providers_allowed(user):
    """Get the provides that the user who is logged is allowed to manage

    Args:
        user (User): Instance of the user that logged into the app

    Returns:
        List: List with all the providers that a specific user can manage
    """

    providers = Provider.objects.all()
    providers_allowed = []
    for provider in providers:
        if user in provider.users.all():
            providers_allowed.append(provider)
    return providers_allowed


def get_employees_allowed(user):
    """Get the employees that the user who is logged can visualize

    Args:
        user (User): Instance of the user that logged into the app

    Returns:
        List: List with all the employees that a specific user can visualize
    """
    employees_allowed = []
    
    providers = get_providers_allowed(user)
    employees = Employee.objects.all()
    
    for employee in employees:
        if  employee.provider in providers or employee.user == user:
            employees_allowed.append(employee)

    return employees_allowed

def total_month_shifts(shifts):
    
    total_shifts = 0
    for shift in shifts:
        total_shifts += shift.employees.count()
    return total_shifts


def calc_wages(shifts, providers):
    """Calculate how much will cost every employee in every shift of the given list of shifts
    it filters the shifts only to summarize the ones corresponding to the given list of providers

    Args:
        shifts (List): List with all the shifts that has to be calculated the total
        providers (Providers): List with all the providers that shifts has to be 
                               filtered

    Returns:
        List: A list containing a dictionary with the employee name as a key, and the number of shifts
              worked as values, and the second item in the list is the salary that the employee will 
              charge to the company
    """

    wages = {}
    salary = 0
    for shift in shifts:
        if shift.shift_provider in providers:
            employees = shift.employees.all()
            for employee in employees:
                if shift.service_provided:
                    salary = shift.service_provided.servicefee.salary
                else:
                    salary = 0
                key = employee.first_name + " " + employee.last_name
                if key in wages:
                    wages[key] = [wages.get(key)[0] + 1, salary]
                else:
                    wages[key] = [1,salary]

    return wages


def calc_total(wages):
    """ Calculate the total amount in euros of all the wages specified

    Args:
        wages (Dict): dictionary with the employee name as a key, and the number of shifts
                      worked as values
        salary (_type_): salary that the employee will recieve for every shift

    Returns:
        Float: Total amount in euros of the cost of all the wages specified
    """

    total_wages = 0
    for name,list in wages.items():
        list[1] = int(list[0]) * int(list[1])
        wages[name] = list
        total_wages += list[1]
    return total_wages


def group_list(list, num):
    """transform a list in a list of list of as much item as specified

    Args:
        list (list): list that is going to be procesed
        num (int): number of items per group

    Returns:
        list: list of lists grouped in groups on num
    """
    grouped_list = []
    init = 0
    end = num

    if len(list)%num:
        iterations = int(len(list)/num) + 1
    else:
        iterations = int(len(list))
    for iteration in range(iterations):
        grouped_list.append(list[init:end])
        init = end
        end += num
    return grouped_list


def get_expenses(invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    shifts = Shift.objects.filter(invoice=invoice)
    expenses = 0
    for shift in shifts:
        expenses += shift.employees.count() * shift.service_provided.servicefee.salary
        
    return expenses
# End of functions

# Views
def index(request):
    """Index view, main view that will be displayed after login
       provides a form and a calendar with a default current date and a list
       of all the shifts that have been created the selected date (month/year)

    Args:
        request (Request): Request from the client

    Returns:
        render: Renders the view with the context specified
    """

    # Permissions for the View
    all_groups = request.user.groups.values_list('name',flat = True) # QuerySet Object
    list_groups = list(all_groups)
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_superuser:
        if "employees" in list_groups:
            return HttpResponseRedirect(reverse("employeedashboard"))
        elif "venues" in list_groups:
            return HttpResponseRedirect(reverse("venuedashboard"))
        elif "providers" in list_groups:
            return HttpResponseRedirect(reverse("providerdashboard"))
        elif "diets" in list_groups:
            return HttpResponseRedirect(reverse("indexdiets"))
        
    # Get context values
    if request.method == "POST":
        month = int(request.POST["month"])
        monthtext = MONTHS.get(str(month))
        year = int(request.POST["year"])
        cal = calendar.Calendar().monthdatescalendar(year,month)
    else:
        cal = calendar.Calendar().monthdatescalendar(CURRENT_YEAR,CURRENT_MONTH)
        monthtext = MONTHS.get(str(CURRENT_MONTH))
        month = CURRENT_MONTH
        year = CURRENT_YEAR
    shift_data = Shift.objects.filter(date__month=month, date__year=year).order_by('date')
    grouped_shifts = group_list(list=shift_data, num=3)
    providers = Provider.objects.all()
    venues = Venue.objects.all()
    employees = Employee.objects.all()

    # Render the view
    return render(request, 'security/index.html', {
        "shifts": shift_data,
        "providers": providers,
        "venues": venues,
        "employees": employees,
        "grouped_shifts": grouped_shifts,
        "cal":cal,
        "year_choice": YEARS_CHOICE,
        "year": year,
        "months": MONTHS,
        "monthtext": monthtext,
        "month": month,
        "days": DAYS,
    })


def dashboard(request, shift_id):
    """Index view, main view that will be displayed after login
       provides a form and a calendar with a default current date and a list
       of all the shifts that have been created the selected date (month/year)

    Args:
        request (Request): Request from the client

    Returns:
        render: Renders the view with the context specified
    """

    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_superuser:
        if request.user.is_staff:
            return HttpResponseRedirect(reverse("rota"))
        else:
            return HttpResponseRedirect(reverse("invoicefilter"))
        
    # Get context values
    shift = Shift.objects.get(pk=shift_id)
    
    if request.method == "POST":
        month = int(request.POST["month"])
        monthtext = MONTHS.get(str(month))
        year = int(request.POST["year"])
        venue = Venue.objects.get(pk=int(request.POST["venue"]))
        provider = Provider.objects.get(pk=int(request.POST["provider"]))
        cal = calendar.Calendar().monthdatescalendar(year,month)
        
    else:
        dateref = shift.date
        cal = calendar.Calendar().monthdatescalendar(dateref.year, dateref.month)
        monthtext = MONTHS.get(str(dateref.month))
        month = dateref.month
        year = dateref.year
        venue = shift.venue
        provider = shift.shift_provider
        
    shift_data = Shift.objects.filter(date__month=month, venue=venue, shift_provider=provider)
    providers = Provider.objects.all()
    venues = Venue.objects.all()
    employees = Employee.objects.all()

    # Render the view
    return render(request, 'security/dashboard.html', {
        "shifts": shift_data,
        "providers": providers,
        "provider": provider,
        "venue": venue,
        "venues": venues,
        "employees": employees,
        "cal":cal,
        "year": year,
        "monthtext": monthtext,
        "month": month,
    })


def addshift(request):
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_superuser:
        return HttpResponseRedirect(reverse("invoicefilter"))
    # Get context values and saves the values to the db
    if request.method == "POST":
        form = ShiftForm(request.POST)
        if form.is_valid():
            shift = form.save()
        else:
            form = ShiftForm() 
    # Redirect the view
    return HttpResponseRedirect(reverse("setservice", args=("admin",shift.pk,)))


def setservice(request, shift_id):
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    
    # Get context values and saves the values to the db
    shift = Shift.objects.get(pk=shift_id)
    provider = shift.shift_provider
    employees = Employee.objects.filter(provider=provider)
    services = provider.services.all()
    if shift.service_provided:
        service = shift.service_provided
        service_selected = True
    else:
        if request.method == "POST":
            service_id = request.POST["service"]
            service = Service.objects.get(pk=service_id)
            shift.service_provided = service
            shift.save()
            service_selected = True
        else:
            service_selected = False
            service = services
    working = shift.employees.filter(provider=provider)
    num_emp = len(working)
    not_working = []
    for emp in employees:
        if emp not in working and emp.provider == provider:
            not_working.append(emp)
    # Redirect the view
    return HttpResponseRedirect(reverse("dashboard", args=(shift.pk,)))
    # Render the view
    #return render(request, 'security/set.html', {
    #    "services": services,
    #    "editshift": shift,
    #    "working": working,
    #    "num_emp": num_emp,
    #    "not_working": not_working,
    #    "service_selected": service_selected,
    #    "service": service,
    #    "reverse": reverse,
    #})


def addemployee(request, shift_id):
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    # Get context values
    shift = Shift.objects.get(pk=shift_id)
    if request.method == "POST":
        employee_id = request.POST["employee"]
        employee = Employee.objects.get(pk=employee_id)
        shift.employees.add(employee)
    # Redirect the view
    return HttpResponseRedirect(reverse("dashboard", args=(shift.pk,)))
    #return HttpResponseRedirect(reverse("setservice", args=("admin",shift_id,)))


def deleteemployeeshift(request, shift_id, employee_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    shift = Shift.objects.get(pk=shift_id)
    employee = Employee.objects.get(pk=employee_id)
    shift.employees.remove(employee)

    return HttpResponseRedirect(reverse("dashboard", args=(shift.pk,)))
    # return HttpResponseRedirect(reverse("setservice", args=("admin", shift_id,)))

    
def invoiceGen(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_superuser:
        return HttpResponseRedirect(reverse("invoicefilter"))
    
    amount = 0
    success = False
    shifts = []
    if request.method == "POST":
        month = request.POST['month']
        year = request.POST['year']
        venue_id = request.POST['invoice_venue']
        provider_id = request.POST['invoice_provider']
        venue = Venue.objects.get(pk=venue_id)
        provider = Provider.objects.get(pk=provider_id)
        
        shifts = Shift.objects.filter(venue=venue, shift_provider=provider, date__year=year, date__month=month)

        if shifts:
            performance = Performance.objects.filter(performance_provider=provider, month=month, year=year)
            if not performance:
                performance = Performance(performance_provider=provider, month=month, year=year)
                performance.save()
            else:
                performance = Performance.objects.get(performance_provider=provider, month=month, year=year)
            
            invoice = Invoice(performance=performance,
                              invoice_venue=venue,
                              invoice_provider=provider,
                              month=month,
                              year=year
                            )
            invoice.save()
        else:
            return HttpResponseRedirect(reverse("invoicegen"))

        for shift in shifts:
            working_number = shift.employees.count()
            if not shift.service_provided or not working_number:
                continue
            fee = shift.service_provided.servicefee.fee
            total_shift = working_number * fee
            amount += total_shift
            shift.invoiced = True
            shift.invoice = invoice
            shift.save()
        invoice.amount = amount
        invoice.save()
        if performance.income:
            performance.income += amount
        else:
            performance.income = amount
        performance.save()
        success = True
    
    return render(request, 'security/invoices/invoice_gen.html', {
        "venues": Venue.objects.all(),
        "providers": Provider.objects.all(),
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "success": success,
        "shifts": shifts,
    })


def invoicefilter(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if request.user.is_staff:
        if not request.user.is_superuser:
            superuser = False
            return HttpResponseRedirect(reverse("rota"))
        else:
            superuser = True
    if not request.user.is_superuser:
        superuser = False
    else:
        superuser = True      

    month = CURRENT_MONTH
    year = CURRENT_YEAR
    
    return render(request, 'security/invoices/invoice_filter.html', {
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "superuser": superuser
    })


def invoicefreport(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if request.user.is_staff:
        if not request.user.is_superuser:
            superuser = False
            return HttpResponseRedirect(reverse("rota"))
        else:
            superuser = True
    if not request.user.is_superuser:
        superuser = False
    else:
        superuser = True      

    invoices_filtered = []
    venues_allowed = get_venues_allowed(request.user)
    providers_allowed = get_providers_allowed(request.user)
    month = CURRENT_MONTH
    year = CURRENT_YEAR

    if request.method == "POST":
        month = request.POST['month']
        year = request.POST['year']
    invoices = Invoice.objects.filter(year=year, month=month)

    for invoice in invoices:
        if providers_allowed:
            if invoice.invoice_provider in providers_allowed:
                if invoice.invoice_venue in venues_allowed:
                    invoices_filtered.append(invoice)
        else:
            if invoice.invoice_venue in venues_allowed:
                invoices_filtered.append(invoice)

    return render(request, 'security/invoices/invoice_filter_report.html', {
        "invoices": invoices_filtered,
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "superuser": superuser
    })


def invoicedetail(request, invoice_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    
    invoice = Invoice.objects.get(pk=invoice_id)
    shifts = Shift.objects.filter(invoice=invoice)
    total_shifts = total_month_shifts(shifts)
    
    return render(request, 'security/invoices/invoice_detail.html', {
        "invoice": invoice,
        "shifts": shifts,
        "total_shifts": total_shifts,
    })


def invoicepdf(request, invoice_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    
    invoice = Invoice.objects.get(pk=invoice_id)
    shifts = Shift.objects.filter(invoice=invoice)
    total_shifts = 0
    for shift in shifts:
        total_shifts += shift.employees.count()
    context = {
        "invoice": invoice,
        "shifts": shifts,
        "total_shifts": total_shifts,
    }
    html = render_to_string("security/invoices/invoice_pdf.html", context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; invoice.pdf"

    font_config = FontConfiguration()
    HTML(string=html).write_pdf(response, font_config=font_config)

    return response


def wagespdf(request, month, year, provider_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        return HttpResponseRedirect(reverse("invoicefilter"))
    
    provider = Provider.objects.get(pk=provider_id)
    shifts = Shift.objects.filter(date__year=year, date__month=month, shift_provider=provider)
    #if request.method == "POST":
    #    month = request.POST['month']
    #    year = request.POST['year']
    #    provider_id = request.POST['wages_provider']
    #    provider = Provider.objects.get(pk=provider_id)
    #    shifts = Shift.objects.filter(date__year=year, date__month=month, shift_provider=provider)
    #else:
    #    shifts = Shift.objects.filter(date__year=year, date__month=month)
    result = calc_wages(shifts=shifts, providers=providers_allowed)
    wages = result
    total_wages = calc_total(wages=wages)

    context = {
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "wages": wages,
        "provider": provider,
        "providers": providers_allowed,
        "total_wages": total_wages,
    }
    html = render_to_string("security/wages/wages_pdf.html", context)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; invoice.pdf"
    font_config = FontConfiguration()
    HTML(string=html).write_pdf(response, font_config=font_config)
    return response
    

def wagesemployeepdf(request, month, year, employee_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        if not request.user.is_staff:
            return HttpResponseRedirect(reverse("invoicefilter"))
    
    
    employee = Employee.objects.get(pk=employee_id)
    shifts = Shift.objects.filter(date__year=year, date__month=month)
    worked_shifts = []
    total_wages = 0
    for shift in shifts:
        if employee in shift.employees.all():
            worked_shifts.append(shift)
    for shift in worked_shifts:
        total_wages += shift.service_provided.servicefee.salary
        
    context = {
        "shifts": shifts,
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "worked_shifts": worked_shifts,
        "total_shifts": len(worked_shifts),
        "total_wages": total_wages,
        "employee": employee,
    }
    html = render_to_string("security/wages/wages_employee_pdf.html", context)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; Wages.pdf"
    font_config = FontConfiguration()
    HTML(string=html).write_pdf(response, font_config=font_config)
    return response
    

def setfullmonth(request):
    if request.method == "POST":
        month = int(request.POST["month"])
        year = int(request.POST["year"])
        venue = Venue.objects.get(pk=int(request.POST["venue"]))
        provider = Provider.objects.get(pk=int(request.POST["provider"]))
        dias = calendar.monthrange(year,month)[1]
        for dia in range(dias):
            dia += 1
            date = datetime.datetime(year,month,dia)
            shift = Shift(venue=venue, date=date, shift_provider=provider)
            shift.save()
    return HttpResponseRedirect(reverse("index"))


def employeedashboard(request):
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("invoicefilter"))
    set = False

    # Get context values

    empleado = None
    if request.user.is_superuser:
        employees = Employee.objects.all()
        empleado = [employee for employee in employees][0]
    else:
        employees = Employee.objects.filter(user=request.user)
        empleado = [employee for employee in employees if employee.user == request.user][0]
        set = True
     
    monthtext = MONTHS.get(str(CURRENT_MONTH))
    month = CURRENT_MONTH
    year = CURRENT_YEAR

    if request.method == "POST":
        empleado = Employee.objects.get(pk=request.POST["employee"])
        month = int(request.POST["month"])
        year = int(request.POST["year"])
        monthtext = MONTHS.get(str(month))
        set = True
        
    cal = calendar.Calendar().monthdatescalendar(year,month)
    shift_data = Shift.objects.filter(date__month=month, date__year=year).order_by('date')
    filtered_days = [shift.date for shift in shift_data if empleado in shift.employees.all()]
    filtered_shifts = [{shift.date:shift.venue} for shift in shift_data if empleado in shift.employees.all()]
    total_shifts = total_month_shifts([shift for shift in shift_data if empleado in shift.employees.all()])
    providers = Provider.objects.all()
    venues = Venue.objects.all()

    worked_shifts = []
    total_wages = 0
    for shift in shift_data:
        if empleado in shift.employees.all():
            worked_shifts.append(shift)
    for shift in worked_shifts:
        total_wages += shift.service_provided.servicefee.salary
    
    # Render the view
    return render(request, 'security/employeedashboard.html', {
        "shifts": shift_data,
        "total_shifts": total_shifts,
        "filtered_shifts": filtered_shifts,
        "filtered_days": filtered_days,
        "providers": providers,
        "venues": venues,
        "employee": empleado,
        "employees": employees,
        "cal":cal,
        "year_choice": YEARS_CHOICE,
        "year": year,
        "months": MONTHS,
        "monthtext": monthtext,
        "month": month,
        "days": DAYS,
        "set": set,
        "worked_shifts": worked_shifts,
        "total_shifts": len(worked_shifts),
        "total_wages": total_wages,
    })


def venuedashboard(request):
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_superuser:
        if request.user.is_staff:
            return HttpResponseRedirect(reverse("rota"))
    
    # Get context values
        
    all_groups = request.user.groups.values_list('name',flat = True) # QuerySet Object
    list_groups = list(all_groups)                                     # QuerySet to `list`

    
    venue = Venue.objects.filter(users__in=[request.user])[0]
    
        
    set= False
    
    monthtext = MONTHS.get(str(CURRENT_MONTH))
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    if request.method == "POST":
        venue = Venue.objects.get(pk=request.POST["venue"])
        month = int(request.POST["month"])
        year = int(request.POST["year"])
        monthtext = MONTHS.get(str(month))
        set = True

    cal = calendar.Calendar().monthdatescalendar(year,month)
    shift_data = Shift.objects.filter(date__month=month, date__year=year).order_by('date')
    filtered_days = [shift.date for shift in shift_data if shift.venue == venue]
    total_shifts = total_month_shifts([shift for shift in shift_data if shift.venue == venue])
    venues_allowed = get_venues_allowed(request.user)
    providers_allowed = get_providers_allowed(request.user)

    invoices_filtered = []
    invoices = Invoice.objects.filter(year=year, month=month)
    for invoice in invoices:
        if providers_allowed:
            if invoice.invoice_provider in providers_allowed:
                if invoice.invoice_venue in venues_allowed:
                    invoices_filtered.append(invoice)
        else:
            if invoice.invoice_venue in venues_allowed:
                invoices_filtered.append(invoice)
   

    # Render the view
    return render(request, 'security/venuedashboard.html', {
        "shifts": shift_data,
        "total_shifts": total_shifts,
        "filtered_days": filtered_days,
        "venues": venues_allowed,
        "providers": providers_allowed,
        "venue": venue,
        "cal":cal,
        "year_choice": YEARS_CHOICE,
        "year": year,
        "months": MONTHS,
        "monthtext": monthtext,
        "month": month,
        "days": DAYS,
        "set": set,
        "invoices": invoices_filtered,
    })


def providerdashboard(request):
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_superuser:
        if request.user.is_staff:
            return HttpResponseRedirect(reverse("rota"))
    
    # Get context values
    provider = Provider.objects.filter(users__in=[request.user])[0]   
    set= False
    monthtext = MONTHS.get(str(CURRENT_MONTH))
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    if request.method == "POST":
        provider = Provider.objects.get(pk=request.POST["provider"])
        month = int(request.POST["month"])
        year = int(request.POST["year"])
        monthtext = MONTHS.get(str(month))
        set = True

    cal = calendar.Calendar().monthdatescalendar(year,month)
    shift_data = Shift.objects.filter(date__month=month, date__year=year, shift_provider=provider).order_by('date')
    filtered_days = [shift.date for shift in shift_data if shift.shift_provider == provider]
    total_shifts = total_month_shifts([shift for shift in shift_data if shift.shift_provider == provider])

    venues_allowed = get_venues_allowed(request.user)
    providers_allowed = get_providers_allowed(request.user)

    invoices_filtered = []
    invoices = Invoice.objects.filter(year=year, month=month)
    for invoice in invoices:
        if providers_allowed:
            if invoice.invoice_provider in providers_allowed:
                if invoice.invoice_venue in venues_allowed:
                    invoices_filtered.append(invoice)
        else:
            if invoice.invoice_venue in venues_allowed:
                invoices_filtered.append(invoice)

    wages = calc_wages(shifts=shift_data, providers=providers_allowed)
    total_wages = calc_total(wages=wages)

    performances = Performance.objects.filter(year=year, performance_provider=provider).order_by('month')
    
    performance_dict = get_performance_dict(performances)
    totals = get_totals_performances(performance_dict)    

    
    # Render the view
    return render(request, 'security/providerdashboard.html', {
        "shifts": shift_data,
        "total_shifts": total_shifts,
        "filtered_days": filtered_days,
        "venues": venues_allowed,
        "providers": providers_allowed,
        "provider": provider,
        "cal":cal,
        "year_choice": YEARS_CHOICE,
        "year": year,
        "months": MONTHS,
        "monthtext": monthtext,
        "month": month,
        "days": DAYS,
        "set": set,
        "invoices": invoices_filtered,
        "wages": wages,
        "total_wages": total_wages,
        "performances": performance_dict,
        "totals": totals,
    })


def performance_filter(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        return HttpResponseRedirect(reverse("invoicefilter"))
    
    year = CURRENT_YEAR
    
    return render(request, 'security/performance/performance_filter.html', {
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "providers": providers_allowed,
    })


def performance_list(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        return HttpResponseRedirect(reverse("invoicefilter"))

    if request.method == "POST":
        year = int(request.POST["year"])
        provider_id = request.POST["provider"]
        provider = Provider.objects.get(pk=provider_id)
        performances = Performance.objects.filter(year=year, performance_provider=provider).order_by('month')
    
    performance_dict = get_performance_dict(performances)
    totals = get_totals_performances(performance_dict)    

    return render(request, 'security/performance/performance_list.html', {
        "performances": performance_dict,
        "provider_id": provider_id,
        "year": year,
        "provider": provider,
        "totals": totals,
    })


def performance_update(request, performance_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        return HttpResponseRedirect(reverse("invoicefilter"))
    
    performance = Performance.objects.get(pk=performance_id)
    performances = []
    performances.append(performance)

    performance_dict = get_performance_dict(performances)

    income = performance_dict[performance][0]
    wages = performance_dict[performance][1]
    ss = performance.ss
    irpf = performance.irpf
    gestoria = performance.gestoria

    if request.method == "POST":
        ss= float(request.POST["ss"])
        irpf= float(request.POST["irpf"])
        gestoria= float(request.POST["gestoria"])
        performance.ss = ss
        performance.irpf = irpf
        performance.gestoria = gestoria
        performance.save()
        performances = Performance.objects.filter(year=performance.year, performance_provider=performance.performance_provider).order_by('month')
        performance_dict = get_performance_dict(performances)
        totals = get_totals_performances(performance_dict)
        return render(request, 'security/performance/performance_list.html', {
            "performances": performance_dict,
            "provider_id": performance.performance_provider.pk,
            "year": performance.year,
            "provider": performance.performance_provider,
            "totals": totals,
        })

          
    return render(request, 'security/performance/performance_update.html', {
        "performance_id": performance_id,
        "performance":performance,
        "income": income,
        "wages": wages,
        "ss": ss,
        "irpf": irpf,
        "gestoria": gestoria,

    })


def get_performance_dict(performances):
    income = 0
    wages = 0
    performance_dict = {}

    for performance in performances:
        invoices = Invoice.objects.filter(performance=performance)
        for invoice in invoices:
            income += invoice.amount
            wages += get_expenses(invoice.pk)
        
        if performance.ss:    
            ss = round(float(performance.ss),2)
        else:
            ss = 0
            
        if performance.irpf:
            irpf = round(float(performance.irpf),2)
        else:
            irpf = 0

        if performance.gestoria:
            gestoria = round(float(performance.gestoria),2)
        else:
            gestoria = 0

        balance = income - wages - ss - irpf - gestoria
        impuesto = round(balance * 0.25,2)
        resultado = round(balance - impuesto,2)
        performance_dict[performance] = [income, wages, ss, irpf, gestoria, balance, impuesto, resultado]
        income = 0
        wages = 0
        ss = 0
        irpf = 0
        gestoria = 0
        balance = 0
        
    return performance_dict

def get_totals_performances(performance_dict):
    income_total = 0
    wages_total = 0
    ss_total = 0
    irpf_total = 0
    gestoria_total = 0
    balance_total = 0
    impuesto_total = 0
    resultado_total = 0
    for perf, numbers in performance_dict.items():
        income_total += numbers[0]
        wages_total += numbers[1]
        ss_total += numbers[2]
        irpf_total += numbers[3]
        gestoria_total += numbers[4]
        balance_total += numbers[5]
        impuesto_total += numbers[6]
        resultado_total += numbers[7]
    totals =[round(income_total, 2), round(wages_total, 2), round(ss_total, 2), round(irpf_total, 2), round(gestoria_total, 2), round(balance_total, 2), round(impuesto_total, 2), round(resultado_total, 2)]
    return totals

class ChartData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, year, provider_id, format=None):
        labels = []
        default_items = []
        provider = Provider.objects.get(pk=provider_id)
        performances = Performance.objects.filter(year=year, performance_provider=provider).order_by('month')
        performance_dict = get_performance_dict(performances)
        for perf, values in performance_dict.items():
            month =  MONTHS.get(str(perf.month))
            labels.append(month)
            default_items.append(values[7])
        
        data = {
                "labels": labels,
                "default": default_items,
        }
    
        return Response(data)
    
class ChartRotaData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, month, year, venue_id, format=None):
        labels = []
        default_items = []
        venue = Venue.objects.get(pk=venue_id)
        
        invoices = Invoice.objects.filter(month=month, year=year, invoice_venue=venue)
        for invoice in invoices:                 
            labels.append(invoice.invoice_provider.name)
            default_items.append(invoice.amount)
        
        data = {
                "labels": labels,
                "default": default_items,
        }
    
        return Response(data)
    





















# LEGACY CODE------------------------------------------------------------------------------
"""
def filtershift(request, date=TODAY):
   
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_superuser:
        if request.user.is_staff:
            return HttpResponseRedirect(reverse("rota"))
        else:
            return HttpResponseRedirect(reverse("invoicefilter"))
    # Get context values
    shift_data = Shift.objects.filter(date=date)
    grouped_shifts = group_list(list=shift_data, num=3)
    # Render the view
    return render(request, 'security/filter.html', {
        "venues": Venue.objects.all(),
        "providers": Provider.objects.all(),
        "shifts": shift_data,
        "grouped_shifts": grouped_shifts,
        "service_selected": False,
        "date": date,
        "date_selected": True,
    })

def rota(request):
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_staff:
            return HttpResponseRedirect(reverse("invoicefilter"))
    set = False
    # Get context values
    empleado = None
    if request.user.is_superuser:
        employees = Employee.objects.all()
    else:
        employees = Employee.objects.filter(user=request.user)
        empleado = [employee for employee in employees if employee.user == request.user][0]
        set = True
    
    monthtext = MONTHS.get(str(CURRENT_MONTH))
    month = CURRENT_MONTH
    year = CURRENT_YEAR

    if request.method == "POST":
        empleado = Employee.objects.get(pk=request.POST["employee"])
        month = int(request.POST["month"])
        year = int(request.POST["year"])
        monthtext = MONTHS.get(str(month))
        set = True

    providers = Provider.objects.all()
    venues = Venue.objects.all()
   

    # Render the view
    return render(request, 'security/rota.html', {
        "providers": providers,
        "venues": venues,
        "employee": empleado,
        "employees": employees,
        "year_choice": YEARS_CHOICE,
        "year": year,
        "months": MONTHS,
        "monthtext": monthtext,
        "month": month,
        "days": DAYS,
        "set": set,
    })

def rotavenue(request):
    # Permissions for the View
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    if not request.user.is_superuser:
        if request.user.is_staff:
            return HttpResponseRedirect(reverse("rota"))
    
    # Get context values
    set= False
    venue = None
    monthtext = MONTHS.get(str(CURRENT_MONTH))
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    
    venues_allowed = get_venues_allowed(request.user)
    providers_allowed = get_providers_allowed(request.user)
   

    # Render the view
    return render(request, 'security/rotavenue.html', {
        "venues": venues_allowed,
        "providers": providers_allowed,
        "venue": venue,
        "year_choice": YEARS_CHOICE,
        "year": year,
        "months": MONTHS,
        "monthtext": monthtext,
        "month": month,
        "days": DAYS,
        "set": set,
    })

def wagesfilter(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        return HttpResponseRedirect(reverse("invoicefilter"))
    
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    
    
    return render(request, 'security/wages/wages_filter.html', {
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "providers": providers_allowed,
    })

def wagesfreport(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        return HttpResponseRedirect(reverse("invoicefilter"))
    
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    if request.method == "POST":
        month = request.POST['month']
        year = request.POST['year']
        provider_id = request.POST['wages_provider']
        provider = Provider.objects.get(pk=provider_id)
        shifts = Shift.objects.filter(date__year=year, date__month=month, shift_provider=provider)
    else:
        shifts = []
    wages = calc_wages(shifts=shifts, providers=providers_allowed)
    total_wages = calc_total(wages=wages)
    
    return render(request, 'security/wages/wages_filter_report.html', {
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "wages": wages,
        "provider": provider,
        "providers": providers_allowed,
        "total_wages": total_wages,
    })

def wagesfilterpdf(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        return HttpResponseRedirect(reverse("invoicefilter"))
    
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    
    return render(request, 'security/wages/wages_filter_pdf.html', {
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "providers": providers_allowed,
    })

def wagesemployee(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        if not request.user.is_staff:
            return HttpResponseRedirect(reverse("invoicefilter"))
    
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    employees = get_employees_allowed(request.user)
    employee = None
    show = False
    
    shifts = Shift.objects.filter(date__year=year, date__month=month)
    worked_shifts = []
    total_wages = 0
    for shift in shifts:
        if employee in shift.employees.all():
            worked_shifts.append(shift)
    for shift in worked_shifts:
        total_wages += shift.service_provided.servicefee.salary
    
    return render(request, 'security/wages/wages_employee.html', {
        "shifts": shifts,
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "worked_shifts": worked_shifts,
        "total_shifts": len(worked_shifts),
        "employees": employees,
        "employee": employee,
        "show":show,
        "total_wages": total_wages,
    })

def wagesereport(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        if not request.user.is_staff:
            return HttpResponseRedirect(reverse("invoicefilter"))
    
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    employees = get_employees_allowed(request.user)
    employee = None
    show = False
    if request.method == "POST":
        month = request.POST['month']
        year = request.POST['year']
        employee_id = request.POST['wages_employee']
        employee = Employee.objects.get(pk=employee_id)
        show = True
    shifts = Shift.objects.filter(date__year=year, date__month=month)
    worked_shifts = []
    total_wages = 0
    for shift in shifts:
        if employee in shift.employees.all():
            worked_shifts.append(shift)
    for shift in worked_shifts:
        total_wages += shift.service_provided.servicefee.salary
    
    return render(request, 'security/wages/wages_employee_report.html', {
        "shifts": shifts,
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "worked_shifts": worked_shifts,
        "total_shifts": len(worked_shifts),
        "employees": employees,
        "employee": employee,
        "show":show,
        "total_wages": total_wages,
    })


def wagesemployeefilter(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    providers_allowed = get_providers_allowed(request.user)
    if not providers_allowed:
        if not request.user.is_staff:
            return HttpResponseRedirect(reverse("invoicefilter"))
    
    month = CURRENT_MONTH
    year = CURRENT_YEAR
    employees = get_employees_allowed(request.user)
    
    return render(request, 'security/wages/wages_employee_filter.html', {
        "month": month,
        "year": year,
        "months": MONTHS,
        "year_choice": YEARS_CHOICE,
        "employees": employees,
    })

class ChartView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'security/performance/performance.html')

"""