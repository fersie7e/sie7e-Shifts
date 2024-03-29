from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    
    path("addshift/",views.addshift,name="addshift"),
    path("add/<int:shift_id>/", views.addemployee, name="addemployee"),
    path("delete/<int:shift_id>/<int:employee_id>", views.deleteemployeeshift, name="deleteemployeeshift"),
    path("set/<int:shift_id>", views.setservice, name="setservice"),

    path("invoice", views.invoiceGen, name="invoicegen"),
    path("invoicefilter/", views.invoicefilter, name="invoicefilter"),
    path("invoicefilter/invoicefreport", views.invoicefreport, name="invoicefreport"),
    path("invoicedetail/<int:invoice_id>", views.invoicedetail, name="invoicedetail"),
    path("invoicepdf/<int:invoice_id>", views.invoicepdf, name="invoicepdf"),
    
    path("wagespdf//<int:month>/<int:year>/<int:provider_id>", views.wagespdf, name="wagespdf"),
    path("wagesemployeepdf/<int:month>/<int:year>/<int:employee_id>", views.wagesemployeepdf, name="wagesemployeepdf"),

    path("setfullmonth/", views.setfullmonth, name="setfullmonth"),

    path("employeedashboard", views.employeedashboard, name="employeedashboard"),
    path("venuedashboard", views.venuedashboard, name="venuedashboard"),
    path("venuedashboard/data/<int:month>/<int:year>/<int:venue_id>", views.ChartRotaData.as_view()),
    path("providerdashboard", views.providerdashboard, name="providerdashboard"),
    path("dashboard/<int:shift_id>", views.dashboard, name="dashboard"),

    path("performance/filter/", views.performance_filter, name="performance-filter"),
    path("performance/list/", views.performance_list, name="performance-list"),
    path("performance/update/<int:performance_id>", views.performance_update, name="performance-update"),
    
    path("performance/data/<int:year>/<int:provider_id>", views.ChartData.as_view()),
    
    #path("filter/<str:date>", views.filtershift, name="filtershift"),
    #path("rota/", views.rota, name="rota"),
    #path("rotavenue/", views.rotavenue, name="rotavenue"),
    #path("wagesfilter/", views.wagesfilter, name="wagesfilter"),
    #path("wagesfilter/wagesfreport", views.wagesfreport, name="wagesfreport"),
    #path("wagesfilterpdf/", views.wagesfilterpdf, name="wagesfilterpdf"),
    #path("wagesemployee/", views.wagesemployee, name="wagesemployee"),
    #path("wagesemployee/wagesereport/", views.wagesereport, name="wagesereport"),
    #path("wagesemployeefilter/", views.wagesemployeefilter, name="wagesemployeefilter"),
    #path("performance/", views.ChartView.as_view(), name="performance"),
    
]