from django.urls import path
from . import views

urlpatterns = [
    path('', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('request-account/', views.StudentRequestView.as_view(), name='student_request'),
    path('thank-you/', views.ThankYouView.as_view(), name='thank_you'),
    path('register-program/', views.RegisterProgramView.as_view(), name='register_program'),
    path('student-dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('student-requests/', views.StudentRequestListView.as_view(), name='student_request_list'),
    path('approve-reject/<int:request_id>/', views.ApproveRejectRequestView.as_view(), name='approve_reject_request'),
    path('add-student/', views.AddStudentView.as_view(), name='add_student'),
    path('create-course/', views.CreateCourseView.as_view(), name='create_course'),
    path('create-program/', views.CreateProgramView.as_view(), name='create_program'),
    path('admin-course-list/', views.AdminCourseListView.as_view(), name='admin_course_list'),
    path('update-grades/', views.UpdateGradesView.as_view(), name='update_grades'),
    path('reset-student-password/', views.ResetStudentPasswordView.as_view(), name='reset_student_password'),
    path('courses/', views.StudentCoursesView.as_view(), name='courses'),
    path('enroll/<int:course_id>/', views.EnrollCourseView.as_view(), name='enroll_course'),
    path('timetable/', views.TimetableView.as_view(), name='timetable'),
    path('grades/', views.GradesView.as_view(), name='grades'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('mark-notification-read/<int:notification_id>/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('course-list/', views.CourseListView.as_view(), name='course_list'),
    path('upload-document/<int:course_id>/', views.UploadDocumentView.as_view(), name='upload_document'),
    path('view-course-documents/<int:course_id>/', views.ViewCourseDocumentsView.as_view(), name='view_course_documents'),
    path('register-program/', views.RegisterProgramView.as_view(), name='register_program'),

]