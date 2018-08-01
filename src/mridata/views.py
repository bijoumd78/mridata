import logging
import os
import numpy as np

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.urls import reverse
from celery.result import AsyncResult

from .models import Data, TempData, Uploader, Project, Message
from .forms import PhilipsDataForm, SiemensDataForm, GeDataForm, IsmrmrdDataForm, DataForm
from .filters import DataFilter
from .tasks import process_ge_data, process_ismrmrd_data, process_philips_data, process_siemens_data


def main(request):
    projects = Project.objects.all().order_by('-name')
    
    return render(request, 'mridata/main.html', {'projects': projects})


def about(request):
    return render(request, 'mridata/about.html')


def faq(request):
    return render(request, 'mridata/faq.html')


def terms(request):
    return render(request, 'mridata/terms.html')


def data_list(request):
    
    filter = DataFilter(request.GET, Data.objects.all().order_by('-upload_date'))

    if request.user.is_authenticated:
        uploader = request.user.uploader
        temp_datasets = TempData.objects.filter(uploader=uploader).order_by('-upload_date')
        messages = Message.objects.filter(user=request.user).order_by('-date_time')
    else:
        temp_datasets = []
        messages = []
    
    if request.is_ajax() and 'page' in request.GET:
        template = 'mridata/data_list_page.html'
    else:
        template = 'mridata/data_list.html'
        
    return render(request, template,
                  {
                      'filter': filter,
                      'temp_datasets': temp_datasets,
                      'messages': messages
                  })


def data_download(request, uuid):
    data = get_object_or_404(Data, uuid=uuid)
    data.downloads += 1
    data.save()

    return redirect(data.ismrmrd_file.url)


def data(request, uuid):
    return render(request, 'mridata/data.html',
                  {'data': get_object_or_404(Data, uuid=uuid)})
    

@login_required
def upload_ismrmrd(request):
    if request.method == "POST":
        form = IsmrmrdDataForm(request.POST, request.FILES)
        if form.is_valid():
            project, created = Project.objects.get_or_create(
                name=form.cleaned_data['project_name'],
            )
            ismrmrd_data = form.save(commit=False)
            ismrmrd_data.project = project
            ismrmrd_data.upload_date = timezone.now()
            ismrmrd_data.uploader = request.user.uploader
            ismrmrd_data.original_filename = request.FILES['ismrmrd_file'].name
            ismrmrd_data.save()

            message = Message(string="{} uploaded. Conversion started.".format(request.FILES['ismrmrd_file'].name),
                              user=request.user)
            message.save()
            
            request.user.uploader.refresh = True
            request.user.uploader.save()
            process_ismrmrd_data.apply_async(args=[ismrmrd_data.uuid],
                                             task_id=str(ismrmrd_data.uuid))
        else:
            return render(request, 'mridata/upload.html', {'form': IsmrmrdDataForm})               
        return redirect('data_list')
    
    return render(request, 'mridata/upload.html', {'form': IsmrmrdDataForm})


@login_required
def upload_ge(request):
    if request.method == "POST":
        form = GeDataForm(request.POST, request.FILES)
        if form.is_valid():
            project, created = Project.objects.get_or_create(
                name=form.cleaned_data['project_name'],
            )
            ge_data = form.save(commit=False)
            ge_data.project = project
            ge_data.upload_date = timezone.now()
            ge_data.uploader = request.user.uploader
            ge_data.original_filename = request.FILES['ge_file'].name
            ge_data.save()
            
            message = Message(string="{} uploaded. Conversion started.".format(request.FILES['ge_file'].name),
                              user=request.user)
            message.save()
            
            request.user.uploader.refresh = True
            request.user.uploader.save()
            process_ge_data.apply_async(args=[ge_data.uuid],
                                        task_id=str(ge_data.uuid))
        else:
            return render(request, 'mridata/upload.html', {'form': GeDataForm})
            
        return redirect('data_list')
    
    return render(request, 'mridata/upload.html', {'form': GeDataForm})


@login_required
def upload_philips(request):
    if request.method == "POST":
        form = PhilipsDataForm(request.POST, request.FILES)
        if form.is_valid():
            project, created = Project.objects.get_or_create(
                name=form.cleaned_data['project_name'],
            )
            philips_data = form.save(commit=False)
            philips_data.project = project
            philips_data.upload_date = timezone.now()
            philips_data.uploader = request.user.uploader
            philips_data.original_filename = (request.FILES['philips_raw_file'].name
                                              + ' ' + request.FILES['philips_sin_file'].name
                                              + ' ' + request.FILES['philips_lab_file'].name)
            
            philips_data.save()
            
            message = Message(string="{} {} {} uploaded. Conversion started.".format(
                request.FILES['philips_raw_file'].name,
                request.FILES['philips_sin_file'].name,
                request.FILES['philips_lab_file'].name),
                              user=request.user)
            message.save()
            
            request.user.uploader.refresh = True
            request.user.uploader.save()
            process_philips_data.apply_async(args=[philips_data.uuid],
                                             task_id=str(philips_data.uuid))
        else:
            return render(request, 'mridata/upload.html', {'form': PhilipsDataForm})

        return redirect('data_list')
    return render(request, 'mridata/upload.html', {'form': PhilipsDataForm})

@login_required
def upload_siemens(request):
    if request.method == "POST":
        form = SiemensDataForm(request.POST, request.FILES)
        if form.is_valid():
            project, created = Project.objects.get_or_create(
                name=form.cleaned_data['project_name'],
            )
            siemens_data = form.save(commit=False)
            siemens_data.project = project
            siemens_data.upload_date = timezone.now()
            siemens_data.uploader = request.user.uploader
            siemens_data.original_filename = request.FILES['siemens_dat_file'].name
            siemens_data.save()
            
            message = Message(string="{} uploaded. Conversion started.".format(
                request.FILES['siemens_dat_file'].name),
                              user=request.user)
            message.save()
            
            request.user.uploader.refresh = True
            request.user.uploader.save()
            process_siemens_data.apply_async(args=[siemens_data.uuid],
                                             task_id=str(siemens_data.uuid))
        else:
            return render(request, 'mridata/upload.html', {'form': SiemensDataForm})
            
        return redirect("data_list")
    
    return render(request, 'mridata/upload.html', {'form': SiemensDataForm})

    
@login_required
def data_edit(request, uuid):
    data = get_object_or_404(Data, uuid=uuid)
    if request.user == data.uploader.user:
        if request.method == "POST":
            form = DataForm(request.POST or None, request.FILES or None, instance=data)
            if form.is_valid():
                project, created = Project.objects.get_or_create(
                    name=form.cleaned_data['project_name'],
                )
                data = form.save(commit=False)
                data.project = project
                data.save()
                
                return redirect("data_list")
        else:
            data = get_object_or_404(Data, uuid=uuid)
            form = DataForm(instance=data, initial={'project_name': data.project.name})
            return render(request, 'mridata/data_edit.html', {'data': data, 'form': form})


@login_required
def data_delete(request, uuid):
    data = get_object_or_404(Data, uuid=uuid)
    if request.user == data.uploader.user:
        data.ismrmrd_file.delete()
        data.thumbnail_file.delete()
        data.delete()
    return redirect("data_list")


@login_required
def temp_data_delete(request, uuid):
    temp_data = get_object_or_404(TempData, uuid=uuid)
    
    if request.user == temp_data.uploader.user:
        temp_data.delete()
    return redirect("data_list")


@login_required
def message_delete(request, pk):
    message = get_object_or_404(Message, pk=pk)
    
    if request.user == message.user:
        message.delete()
    return redirect("data_list")


@login_required
def check_refresh(request):

    if request.user.is_authenticated:

        uploader = request.user.uploader
        if uploader.refresh:
            uploader.refresh = False
            uploader.save()
            return JsonResponse({'refresh' : True})
            
    return JsonResponse({'refresh' : False})
