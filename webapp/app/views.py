from django.shortcuts import render
from django.http import HttpResponse
from .forms import LoginForm

# Create your views here.
def login_form(request):

    form = LoginForm()

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse("Success!")

    return render(request, "index.html", {'form': form})