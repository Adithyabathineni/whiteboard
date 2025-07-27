from django.db import models
from django.contrib.auth.models import User

# Choices for days of the week
DAYS_OF_WEEK = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
    ('Sunday', 'Sunday'),
]

# Choices for semester
SEMESTER_CHOICES = [
    ('Semester 1', 'Semester 1'),
    ('Semester 2', 'Semester 2'),
]

class StudentRequest(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    date_of_birth = models.DateField()
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=15)
    date_of_birth = models.DateField()
    address = models.TextField()
    program = models.ForeignKey('Program', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

class Program(models.Model):
    program_name = models.CharField(max_length=100)

    def __str__(self):
        return self.program_name

class Course(models.Model):
    course_name = models.CharField(max_length=100)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK, default='Monday')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES, default='Semester 1')

    def __str__(self):
        return self.course_name

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=10, blank=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.day_of_week:
            self.day_of_week = self.course.day_of_week
        if not self.start_time:
            self.start_time = self.course.start_time
        if not self.end_time:
            self.end_time = self.course.end_time
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.user.username} enrolled in {self.course.course_name}"

class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    grade = models.CharField(max_length=2)

    def __str__(self):
        return f"{self.student.user.username} - {self.course.course_name}: {self.grade}"

    class Meta:
        unique_together = ('student', 'course')
class CourseDocument(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='course_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.course.course_name} uploaded on {self.uploaded_at}"