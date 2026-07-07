# This file only contains a function to return a testing webpage
from django.http import HttpResponse
from django.shortcuts import render
def test(request) -> HttpResponse:
    return render(request=request,
                  template_name="component.html")
