                                                                                                                                                                        SOURCE CODE:

import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from xhtml2pdf import pisa
from django.template.loader import get_template
import google.generativeai as genai

from .models import UserRegistrationModel
from users.forms import UserRegistrationForm

# ✅ Gemini API setup
genai.configure(api_key="AIzaSyAysVqWZ-Ydq8NTcPZN6QwpVX5JkEDE17Q")

# ✅ Home Page
def base(request):
    return render(request, 'base.html')

# ✅ User Registration View
def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'You have been successfully registered') 
            return render(request, 'UserRegistration.html')
        else:
            messages.error(request, 'Email or Mobile Already Exists')
    else:
        form = UserRegistrationForm()
    return render(request, 'UserRegistration.html', {'form': form})

# ✅ User Login View
def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('password')
        try:
            user = UserRegistrationModel.objects.get(loginid=loginid, password=pswd)
            if user.status == "activated":
                request.session['id'] = user.id
                request.session['loggeduser'] = user.name
                return redirect('UserHome')
            else:
                messages.error(request, 'Your account is not activated.')
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, 'Invalid Login ID or Password')
    return render(request, 'UserLogin.html')

# ✅ User Home View

def UserHome(request):
    return render(request, 'users/UserHome.html')

# ✅ Gemini Utility Function
def call_gemini(prompt):
    try:
        model = genai.GenerativeModel("models/gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Gemini Error: {str(e)}"

# ✅ GenAI Recommender System View (based on base paper)

def genai_recommender_view(request):
    output = ""
    task = ""

    if request.method == 'POST':
        task = request.POST.get("task_type")
        input_text = request.POST.get("input_text", "").strip()

        if task == "generate":
            prompt = f"""Using Generative AI (GANs or VAEs), generate synthetic user-item interaction data for a recommendation system. Context:\n{input_text}"""
        elif task == "cold_start":
            prompt = f"""How can Generative AI (GANs, VAEs, or hybrid models) solve the cold-start problem in the following RS scenario?\n{input_text}"""
        elif task == "diversity":
            prompt = f"""Suggest methods to improve recommendation diversity using GANs or VAEs. Context:\n{input_text}"""
        elif task == "evaluate":
            prompt = f"""Evaluate the given recommendation system design and suggest improvements using Generative AI models (GANs, VAEs, Transformers):\n{input_text}"""
        else:
            prompt = "Invalid task."

        output = call_gemini(prompt)

    return render(request, 'users/genai_recommender.html', {
        "output": output,
        "task": task
    })

# ✅ PDF Export View
def export_pdf(request):
    if request.method == 'POST':
        html = request.POST.get("pdf_content", "")
        template = get_template("users/pdf.html")
        html_content = template.render({'content': html})
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="genai_output.pdf"'
        pisa_status = pisa.CreatePDF(html_content, dest=response)
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
        return response


