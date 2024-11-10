from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Project, Tag
from .forms import ProjectForm, FileUploadForm
from .utils import get_signed_url
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import *
from django.http import JsonResponse
from .models import FileUpload
from django.conf import settings
import boto3
import os
User = get_user_model()

@login_required
def project_files(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    selected_tags = request.GET.getlist('tags')

    if request.method == 'POST':
        if project.created_by == request.user or project.members.filter(id=request.user.id).exists():
            form = FileUploadForm(request.POST, request.FILES)
            if form.is_valid():
                file_upload = form.save(commit=False)
                file_upload.project = project
                file_upload.uploaded_by = request.user
                file_upload.save()

                # Parse keywords and create/associate tags
                keywords = form.cleaned_data['keywords']
                if keywords:
                    tags = [tag.strip() for tag in keywords.split(',')]
                    for tag_name in tags:
                        tag, created = Tag.objects.get_or_create(name=tag_name, project=project)
                        file_upload.tags.add(tag)

                form.save_m2m()
                return redirect('projects:project_files', project_id=project.id)
    else:
        form = FileUploadForm()

    # Current behavior is to just take all files if they have ANY of the selected tags.
    if selected_tags:
        files = project.files.filter(tags__name__in=selected_tags).distinct()
    else:
        files = project.files.all()

    signed_urls = {file: get_signed_url(file) for file in files}
    tags = Tag.objects.filter(project=project).distinct()

    context = {
        'project': project,
        'files': signed_urls,
        'tags': tags,
        'selected_tags': selected_tags,
        'form': form,
    }
    return render(request, 'specific_pages/files.html', context)

@login_required 
def view_file(request, project_id, file_id):
    project = get_object_or_404(Project, id=project_id)
    file_upload = get_object_or_404(FileUpload, id=file_id,project=project)
    
    # Get the signed URL for displaying the file (so that the file is securely accessed from AWS)
    file_url = get_signed_url(file_upload)
    # If file is hosted on AWS S3
    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,region_name=settings.AWS_S3_REGION_NAME)
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    file_key = file_upload.file.name  # This is the path to the file in S3

    # Get the text file content if it is a txt file
    if '.txt' in file_key:
      file_obj = s3.get_object(Bucket=bucket_name, Key=file_key)
      file_content = file_obj['Body'].read().decode('utf-8')  # Decode as utf-8 text
    else: 
        file_content = ''
    context = {
        'project': project,
        'file': file_upload,
        'file_url': file_url,
        'file_content': file_content
    }
    return render(request, 'specific_pages/file.html', context)

@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            return redirect('/')
    else:
        form = ProjectForm()

    return render(request, 'create_project.html', {'form': form})


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if project.created_by == request.user or request.user.permission_level == 'admin':
        return render(request, 'project_detail.html', {'project': project})
    elif project.members.filter(id=request.user.id).exists():
        return render(request, 'project_detail.html', {'project': project})
    else:
        return render(request, 'specific_pages/request_to_join.html', {'project': project})


@login_required
def request_to_join(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    user = request.user

    if project not in user.projects_requested_by_users.all():
        project.requested.add(user)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'message': 'Already requested'})


@login_required
def approve_request(request, project_id, user_id):
    User = get_user_model()
    project = get_object_or_404(Project, id=project_id)
    user = get_object_or_404(User, id=user_id)

    if request.user == project.created_by:
        user.requested_projects.remove(project)
        project.members.add(user)
    return redirect('projects:project-detail', project_id=project_id)


@login_required
def deny_request(request, project_id, user_id):
    User = get_user_model()
    project = get_object_or_404(Project, id=project_id)
    user = get_object_or_404(User, id=user_id)

    if request.user == project.created_by:
        user.requested_projects.remove(project)
        project.denied.add(user)

    return redirect('projects:project-detail', project_id=project_id)


from django.contrib import messages
from .models import Calendar

@login_required
def calendar_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_date = request.POST.get('event_date')
        created_by = request.user
        
        if title and description and event_date:
            event = Calendar(title=title, description=description, event_date=event_date, project=project, created_by=created_by)
            event.save()
            messages.success(request, 'Event added successfully!')
        else:
            messages.error(request, 'Please fill in all fields.')
    events = Calendar.objects.filter(project=project)
    return render(request, 'specific_pages/calendar.html', {'events': events, 'project_id': project_id})

@login_required
def team_handbook_view(request):
    return render(request, 'specific_pages/team_handbook.html')


@login_required
def collaboration_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if project.created_by == request.user:
        return render(request, 'specific_pages/collaboration.html', {'project': project})
    else:
        return redirect('projects:project-detail', project_id=project.id)


@login_required
def todos_view(request, project_id):
    if request.method == 'POST':
        # Process the form data
        description = request.POST.get('description')
        date_due = request.POST.get('date_due')
        priority = request.POST.get('priority')
        assigned_to = request.POST.getlist('assigned_to')
        is_finished = request.POST.get('is_finished', 'off') == 'on'

        # Assuming there's a project_id in the session or a similar way to determine the project
        # project_id = request.session.get('current_project_id')
        project = get_object_or_404(Project, id=project_id)

        # Create a new Todo instance
        todo = Todo(project=project, description=description, date_due=date_due, priority=priority, is_finished=is_finished, created_by=request.user)
        todo.save()

        # Assign users to the todo
        for user_id in assigned_to:
            user = get_object_or_404(User, id=user_id)
            todo.assigned_to.add(user)
        return redirect('/')

    users = User.objects.all()
    todos = Todo.objects.filter(project=project_id)
    return render(request, 'specific_pages/todos.html', {'users': users, 'todos': todos, 'project_id': project_id})
@login_required
def todo_detail(request,todo_id):
    todo = get_object_or_404(Todo, id=todo_id)
    return render(request, 'specific_pages/todo_detail.html', {'todo': todo})

@login_required
def toggle_todo_complete(request, todo_id):
    todo = get_object_or_404(Todo, id=todo_id)
    todo.is_finished = not todo.is_finished
    todo.save()
    return redirect('projects:todo-detail', todo_id=todo.id)



@login_required
def timeline_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        event = request.POST.get('event')
        date = request.POST.get('date')
        if event and date:
            Timeline(project=project, event=event, date=date).save()
    events = Timeline.objects.filter(project=project_id)
    return render(request, 'specific_pages/timeline.html', {'events': events, 'project_id': project_id})


@login_required
def files_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    return render(request, 'specific_pages/files.html', {'project': project})


@login_required
def schedule_meets_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    schedule_meets = ScheduleMeet.objects.filter(project=project)
    return render(request, 'specific_pages/schedule_meets.html', {'project': project, 'schedule_meets': project.schedule_meets.all()})

@login_required
def make_meets(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'POST':
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        description = request.POST.get('description')
        title = request.POST.get('title')
        meeting_date = request.POST.get('meeting_date')
        location = request.POST.get('location')
        partipants = request.POST.getlist('participants')

        meeting = ScheduleMeet(project=project, start_time=start_time, end_time=end_time, description=description, title=title, meeting_date=meeting_date, location=location, partipants=partipants)
        meeting.save()
            
        return redirect('projects:schedule-meets', project_id=project_id)

    schedule_meets = ScheduleMeet.objects.filter(project=project)

    return render(request, 'projects/schedule_meets.html', {'project': project, 'schedule_meets': schedule_meets, 'project_id': project_id})


@require_POST
@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.user.permission_level == 'admin' or project.owner == request.user:
        project.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'You do not have permission to delete this project.'}, status=403)


@login_required
def delete_file(request, project_id, file_id):
    project = get_object_or_404(Project, id=project_id)
    file_to_delete = get_object_or_404(project.files.all(), id=file_id)

    if request.user.permission_level == 'admin':
        file_to_delete.delete()
        return redirect('projects:project_files', project_id=project_id)
    else:
        return redirect('projects:project-detail', project_id=project_id)
    

@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    project.delete()
    return JsonResponse({'success': True})



@login_required
def delete_todo(request, project_id, todo_id):
    project = get_object_or_404(Project, id=project_id)
    todo_to_delete = get_object_or_404(project.todos.all(), id=todo_id)

    
    todo_to_delete.delete()
    return redirect('projects:todos', project_id=project_id)
    

@login_required
def delete_calendar(request, project_id, calendar_id):
    
    calendar_to_delete = get_object_or_404(Calendar, id=calendar_id)

    calendar_to_delete.delete()
    return redirect('projects:calendar', project_id=project_id)
    


@login_required
def delete_event(request, project_id, event_id):
    
    event_to_delete = get_object_or_404(Timeline, id=event_id)

    
    event_to_delete.delete()
    return redirect('projects:timeline', project_id=project_id)
    

