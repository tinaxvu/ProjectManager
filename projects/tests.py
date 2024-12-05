from contextlib import AbstractContextManager
from typing import Any
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Project, Todo, Calendar, ScheduleMeet, Message, Thread, FileUpload, Collaboration
from django.urls import reverse


class Models(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester',email='testuser@gmail.com',password='password')
        self.project = Project.objects.create(name='Test Project',
            description='Testing description', 
            created_by=self.user
            )

    def test_create_project(self):
        self.assertEqual(self.project.name, 'Test Project')
        self.assertEqual(self.project.description, 'Testing description')
        self.assertEqual(self.project.created_by, self.user)
        self.assertTrue(Project.objects.filter(id=self.project.id).exists())
        self.assertTrue(get_user_model().objects.filter(username='tester').exists())

    def test_todo(self):
        self.assertFalse(Todo.objects.filter(description='Test todo').exists())

        todo = Todo.objects.create(
            project=self.project,
            description='Test todo',
            date_due='2028-12-01',
            priority='High',
            created_by=self.user
        )
        self.assertTrue(Todo.objects.filter(description='Test todo').exists())
        self.assertEqual(todo.description, 'Test todo')
        self.assertEqual(todo.date_due, '2028-12-01')
        self.assertFalse(todo.is_finished)

        todo.delete()
        self.assertEqual(Todo.objects.count(), 0)

    def test_calendar_event(self):
        self.assertFalse(Calendar.objects.filter(title='Test event').exists())

        event = Calendar.objects.create(
            project=self.project,
            title='Test event',
            description='Test description',
            event_date='2028-12-01 00:00',
            end_date='2028-12-01 23:59',
            created_by=self.user,
            type='meeting',
        )
        self.assertEqual(event.title, 'Test event')
        self.assertEqual(event.event_date, '2028-12-01 00:00')
        self.assertEqual(event.end_date, '2028-12-01 23:59')
        self.assertEqual(event.project, self.project)
        self.assertTrue(Calendar.objects.filter(title='Test event').exists())

        event.delete()
        self.assertEqual(Calendar.objects.count(), 0)

    def test_schedule_meets(self):
        self.assertFalse(ScheduleMeet.objects.filter(title='Test meeting').exists())

        meeting = ScheduleMeet.objects.create(
            project=self.project,
            title='Test meeting',
            description='Test description',
            meeting_date='2028-12-01',
            start_time='12:00',
            end_time='12:30',
        )
        self.assertEqual(meeting.title, 'Test meeting')
        self.assertTrue(ScheduleMeet.objects.filter(title='Test meeting').exists())
        self.assertTrue(ScheduleMeet.objects.count(), 1)

        meeting.delete()
        self.assertEqual(ScheduleMeet.objects.count(), 0)

    def test_message_board(self):
        self.assertFalse(Thread.objects.filter(title='Test message').exists())
        self.assertFalse(Message.objects.filter(title='Test reply').exists())

        message = Thread.objects.create(
            project=self.project,
            posted_by=self.user,
            title='Test message',
            body='Test body'
        )
        self.assertEqual(message.title, 'Test message')
        self.assertEqual(message.body, 'Test body')

        self.assertFalse(message.pinned)
        message.pinned = True
        message.save()
        self.assertTrue(message.pinned) 

        reply = Message.objects.create(
            project=self.project,
            title='Test reply',
            posted_by=self.user,
            thread=message
        )
        self.assertEqual(reply.title, 'Test reply')
        self.assertEqual(reply.project, self.project)   
        self.assertEqual(reply.thread, message)
        self.assertTrue(Thread.objects.filter(title='Test message').exists())
        self.assertTrue(Message.objects.filter(title='Test reply').exists())
    
        reply.delete()
        self.assertEqual(Thread.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 0)
        message.delete()
        self.assertEqual(Thread.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)

    def test_file_upload(self):
        self.assertFalse(FileUpload.objects.filter(file_title='Test file').exists())

        file = FileUpload.objects.create(
            project=self.project,
            uploaded_by=self.user,
            file='uploads/testfile.txt',
            file_title='Test file',
            description='Test description',
            keywords='test, file, upload'
        )
        self.assertTrue(FileUpload.objects.filter(file_title='Test file').exists())
        self.assertEqual(file.file_title, 'Test file')
        self.assertEqual(file.description, 'Test description')
        self.assertEqual(file.keywords, 'test, file, upload')

        file.delete()
        self.assertFalse(FileUpload.objects.filter(file_title='Test file').exists())
        self.assertEqual(FileUpload.objects.count(), 0)
    
    def test_collaboration(self):
        self.assertFalse(Collaboration.objects.filter(title='Test collaboration').exists())

        collaboration = Collaboration.objects.create(
            project=self.project,
            title='Test collaboration',
            description='Test description',
            created_by=self.user
        )
        self.assertTrue(Collaboration.objects.filter(title='Test collaboration').exists())
        self.assertEqual(collaboration.title, 'Test collaboration')
        self.assertEqual(collaboration.description, 'Test description')
        self.assertEqual(collaboration.created_by, self.user)

    def test_leave_project(self):
        self.project.members.add(self.user)
        self.assertEqual(self.project.members.count(), 1)
        self.project.members.remove(self.user)
        self.assertEqual(self.project.members.count(), 0)
        self.project.delete()
        self.assertFalse(Project.objects.filter(name='Test Project').exists())

class Views(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester',email='testuser@gmail.com',password='password')
        self.project = Project.objects.create(name='Test Project',
            description='Testing description', 
            created_by=self.user
            )
        self.client.login(username='tester', password='password')
        
    def test_project_detail_view(self):
        response = self.client.get(reverse('projects:project-detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'project_detail.html')

    def test_create_project_view(self):
        response = self.client.get(reverse('projects:create-project'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_project.html')
        self.assertTrue(get_user_model().objects.filter(username='tester').exists())

    def test_calendar_view(self):
        response = self.client.get(reverse('projects:calendar', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'specific_pages/calendar.html')

    def test_collaboration_view(self):
        response = self.client.get(reverse('projects:collaboration', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'specific_pages/collaboration.html')
    
    def test_todo_view(self):
        response = self.client.get(reverse('projects:todos', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'specific_pages/todos.html')

    def test_message_board_view(self):
        response = self.client.get(reverse('projects:message_board', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'specific_pages/message_board.html')
    
    def test_schedule_meets_view(self):
        response = self.client.get(reverse('projects:schedule-meets', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'specific_pages/schedule_meets.html')
    
    def test_files_view(self):
        response = self.client.get(reverse('projects:project_files', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'specific_pages/files.html')

    