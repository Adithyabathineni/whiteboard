import logging
import random
import string
from datetime import datetime
from .forms import StudentRequestForm
from django.db.models import Count
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .models import StudentRequest, Student, Notification, Course, Program, Enrollment, Grade, CourseDocument
from .forms import StudentRequestForm, CourseForm, GradeForm, EnrollmentForm
from django.core.files.storage import FileSystemStorage


logger = logging.getLogger(__name__)

class LoginView(View):
    def get(self, request):
        logger.debug("Rendering login page")
        return render(request, 'core/login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        logger.debug(f"Login attempt with username: {username}")
        try:
            user = User.objects.get(username=username)
            logger.debug(f"User found: {username}, Is Active: {user.is_active}, Is Staff: {user.is_staff}")
        except User.DoesNotExist:
            logger.debug(f"User not found: {username}")
            messages.error(request, "Invalid username or password.")
            return render(request, 'core/login.html')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            logger.debug(f"Authentication successful for {username}")
            login(request, user)
            next_url = request.GET.get('next', 'student_dashboard')
            logger.debug(f"Redirecting to {next_url}")
            return redirect(next_url)
        else:
            logger.debug(f"Authentication failed for {username}")
            messages.error(request, "Invalid username or password.")
            return render(request, 'core/login.html')

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')

class StudentRequestView(View):
    def get(self, request):
        form = StudentRequestForm()
        return render(request, 'core/student_request.html', {'form': form})

    def post(self, request):
        form = StudentRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('thank_you')
        return render(request, 'core/student_request.html', {'form': form})
class ThankYouView(View):
    def get(self, request):
        return render(request, 'core/thank_you.html')

class RegisterProgramView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('logout')
        if student.program:
            messages.info(request, "You are already registered for a program.")
            return redirect('student_dashboard')
        programs = Program.objects.all()
        return render(request, 'core/register_program.html', {'programs': programs})

    def post(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('logout')
        if student.program:
            messages.info(request, "You are already registered for a program.")
            return redirect('student_dashboard')
        program_id = request.POST.get('program')
        program = get_object_or_404(Program, id=program_id)
        student.program = program
        student.save()
        # Automatically enroll in all courses in the program
        courses = Course.objects.filter(program=program)
        for course in courses:
            # Check for scheduling conflicts before enrolling
            existing_enrollments = Enrollment.objects.filter(
                student=student,
                day_of_week=course.day_of_week,
                start_time__lt=course.end_time,
                end_time__gt=course.start_time
            )
            if not existing_enrollments.exists():
                Enrollment.objects.create(student=student, course=course)
        messages.success(request, f"You have been registered for {program.program_name} and enrolled in its courses.")
        return redirect('student_dashboard')

class StudentDashboardView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if request.user.is_staff:
            return redirect('admin_dashboard')
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('logout')
        
        # Check if student needs to register for a program
        if not student.program:
            return redirect('register_program')
        
        notifications = Notification.objects.filter(user=request.user)
        enrollments = Enrollment.objects.filter(student=student)
        return render(request, 'core/student_dashboard.html', {
            'student': student,
            'notifications': notifications,
            'enrollments': enrollments
        })
    
class AdminDashboardView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        # Fetch programs and annotate with student count
        programs = Program.objects.all().annotate(student_count=Count('student'))
        total_students = Student.objects.count()
        total_courses = Course.objects.count()
        total_programs = Program.objects.count()
        total_student_requests = StudentRequest.objects.count()
        return render(request, 'core/admin_dashboard.html', {
            'programs': programs,
            'total_students': total_students,
            'total_courses': total_courses,
            'total_programs': total_programs,
            'total_student_requests': total_student_requests
        })
class StudentRequestListView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        requests = StudentRequest.objects.all()
        # Create a list of dictionaries with request data and previewed username
        request_data = []
        for req in requests:
            # Generate base username: firstname + first letter of lastname + month of birth
            first_name = req.first_name.lower().replace(" ", "")  # e.g., "Venky" → "venky"
            last_name_initial = req.last_name[0].lower() if req.last_name else ""  # e.g., "Verma" → "v"
            birth_month = req.date_of_birth.month  # e.g., May → 5
            birth_month_str = f"{birth_month:02d}"  # e.g., 5 → "05"
            base_username = f"{first_name}{last_name_initial}{birth_month_str}"  # e.g., "venkyv05"
            # Check if the base username already exists
            is_duplicate = User.objects.filter(username=base_username).exists()
            request_data.append({
                'request': req,
                'preview_username': base_username,
                'is_duplicate': is_duplicate
            })
        return render(request, 'core/student_request_list.html', {'request_data': request_data})
class ApproveRejectRequestView(LoginRequiredMixin, View):
    login_url = 'login'

    def post(self, request, request_id):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        student_request = get_object_or_404(StudentRequest, id=request_id)
        action = request.POST.get('action')
        if action == 'approve':
            # Generate base username: firstname + first letter of lastname + month of birth
            first_name = student_request.first_name.lower().replace(" ", "")  # e.g., "John" → "john"
            last_name_initial = student_request.last_name[0].lower() if student_request.last_name else ""  # e.g., "Doe" → "d"
            birth_month = student_request.date_of_birth.month  # e.g., January → 1
            birth_month_str = f"{birth_month:02d}"  # e.g., 1 → "01"
            username = f"{first_name}{last_name_initial}{birth_month_str}"  # e.g., "johnd01"

            # Check if username already exists, append a random two-digit number if necessary
            base_username = username
            while User.objects.filter(username=username).exists():
                random_suffix = random.randint(0, 99)  # Generate a random number between 00 and 99
                random_suffix_str = f"{random_suffix:02d}"  # Ensure it's two digits (e.g., 5 → "05")
                username = f"{base_username}{random_suffix_str}"  # e.g., "johnd0105"

            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            user = User.objects.create_user(
                username=username,
                email=student_request.email,
                password=password
            )
            Student.objects.create(
                user=user,
                first_name=student_request.first_name,
                last_name=student_request.last_name,
                phone=student_request.phone,
                date_of_birth=student_request.date_of_birth,
                address=student_request.address
            )
            Notification.objects.create(
                user=user,
                message=f"Your student account has been approved. Username: {user.username}. Please contact the admin to obtain your password."
            )
            messages.success(request, "Student request approved and account created.")
        student_request.delete()
        return redirect('student_request_list')
    
class AddStudentView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        return render(request, 'core/add_student.html')

    def post(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        date_of_birth = request.POST.get('date_of_birth')
        address = request.POST.get('address')
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            Student.objects.create(
                user=user,
                phone=phone,
                date_of_birth=date_of_birth,
                address=address
            )
            messages.success(request, "Student added successfully.")
        except Exception as e:
            messages.error(request, f"Error adding student: {str(e)}")
        return redirect('admin_dashboard')

class CreateCourseView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        form = CourseForm()
        return render(request, 'core/create_course.html', {'form': form})

    def post(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course created successfully.")
            return redirect('admin_course_list')
        return render(request, 'core/create_course.html', {'form': form})

class CreateProgramView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        return render(request, 'core/create_program.html')

    def post(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        program_name = request.POST.get('program_name')
        Program.objects.create(program_name=program_name)
        messages.success(request, "Program created successfully.")
        return redirect('admin_dashboard')

class AdminCourseListView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        courses = Course.objects.all()
        return render(request, 'core/admin_course_list.html', {'courses': courses})

class UpdateGradesView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        form = GradeForm()
        return render(request, 'core/update_grades.html', {'form': form})

    def post(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        form = GradeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Grade updated successfully.")
            return redirect('update_grades')
        return render(request, 'core/update_grades.html', {'form': form})

class ResetStudentPasswordView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        students = Student.objects.all()
        return render(request, 'core/reset_student_password.html', {'students': students})

    def post(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        student_id = request.POST.get('student')
        new_password = request.POST.get('new_password')
        student = get_object_or_404(Student, id=student_id)
        student.user.set_password(new_password)
        student.user.save()
        # Update the notification message to exclude the password
        Notification.objects.create(
            user=student.user,
            message="Your password has been reset. Please contact the admin to obtain your new password."
        )
        messages.success(request, "Password reset successfully.")
        return redirect('reset_student_password')
    
class StudentCoursesView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('logout')
        if not student.program:
            return redirect('register_program')
        enrolled_courses = Enrollment.objects.filter(student=student).values_list('course_id', flat=True)
        available_courses = Course.objects.exclude(id__in=enrolled_courses)
        return render(request, 'core/courses.html', {'courses': available_courses})

class EnrollCourseView(LoginRequiredMixin, View):
    login_url = 'login'

    def post(self, request, course_id):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('logout')
        if not student.program:
            messages.error(request, "You must register for a program before enrolling in additional courses.")
            return redirect('register_program')
        course = get_object_or_404(Course, id=course_id)
        # Check for scheduling conflicts
        existing_enrollments = Enrollment.objects.filter(
            student=student,
            day_of_week=course.day_of_week,
            start_time__lt=course.end_time,
            end_time__gt=course.start_time
        )
        if existing_enrollments.exists():
            messages.error(request, f"Cannot enroll in {course.course_name}. It conflicts with your existing schedule on {course.day_of_week} from {course.start_time} to {course.end_time}.")
            return redirect('courses')
        Enrollment.objects.create(student=student, course=course)
        messages.success(request, f"Enrolled in {course.course_name} successfully.")
        return redirect('courses')

class TimetableView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('logout')
        if not student.program:
            return redirect('register_program')
        enrollments = Enrollment.objects.filter(student=student)
        return render(request, 'core/timetable.html', {'enrollments': enrollments})

class GradesView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('logout')
        if not student.program:
            return redirect('register_program')
        grades = Grade.objects.filter(student=student)
        return render(request, 'core/grades.html', {'grades': grades})

class ProfileView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('logout')
        if not student.program:
            return redirect('register_program')
        return render(request, 'core/profile.html', {'student': student})

class MarkNotificationReadView(LoginRequiredMixin, View):
    login_url = 'login'

    def post(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.read = True
        notification.save()
        messages.success(request, "Notification marked as read.")
        return redirect('student_dashboard')
class CourseListView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        courses = Course.objects.all()
        return render(request, 'core/admin_course_list.html', {'courses': courses})
    

class UploadDocumentView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request, course_id):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        course = get_object_or_404(Course, id=course_id)
        return render(request, 'core/upload_document.html', {'course': course})

    def post(self, request, course_id):
        if not request.user.is_staff:
            return redirect('student_dashboard')
        course = get_object_or_404(Course, id=course_id)
        if 'document' in request.FILES:
            document = request.FILES['document']
            CourseDocument.objects.create(course=course, document=document)
            messages.success(request, f"Document uploaded successfully for {course.course_name}.")
            return redirect('course_list')
        else:
            messages.error(request, "Please select a file to upload.")
        return render(request, 'core/upload_document.html', {'course': course})
class ViewCourseDocumentsView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request, course_id):
        if request.user.is_staff:
            return redirect('admin_dashboard')
        student = get_object_or_404(Student, user=request.user)
        course = get_object_or_404(Course, id=course_id)
        # Check if the student is enrolled in the course
        if not Enrollment.objects.filter(student=student, course=course).exists():
            messages.error(request, "You are not enrolled in this course.")
            return redirect('student_dashboard')
        documents = CourseDocument.objects.filter(course=course)
        return render(request, 'core/view_course_documents.html', {
            'course': course,
            'documents': documents
        })