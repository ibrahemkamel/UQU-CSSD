from django.db import models
from django.contrib.auth.models import User


class Location(models.Model):
    GROUP_CHOICES = [
        ('MALE', 'Male Clinics'),
        ('FEMALE', 'Female Clinics'),
        ('SPECIALTY', 'Specialty Clinics'),
        ('EMERGENCY', 'Emergency Clinics'),
        ('CSSD', 'CSSD'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    group_type = models.CharField(max_length=30, choices=GROUP_CHOICES)

    def __str__(self):
        return self.name


class CSSDTemplate(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class CSSDTemplateItem(models.Model):
    template = models.ForeignKey(CSSDTemplate, on_delete=models.CASCADE, related_name='items')
    instrument_name = models.CharField(max_length=150)
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.template.name} - {self.instrument_name}"


class CSSDRequest(models.Model):
    STATUS_CHOICES = [
        ('SENT_TO_CSSD', 'Sent to CSSD'),
        ('RECEIVED_BY_CSSD', 'Received by CSSD'),
        ('RETURNED_TO_CLINIC', 'Returned to Clinic'),
        ('CONFIRMED_BY_CLINIC', 'Confirmed by Clinic'),
        ('CLOSED', 'Closed'),
    ]

    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    procedure = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='SENT_TO_CSSD')

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_cssd_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    received_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='received_cssd_requests'
    )
    received_at = models.DateTimeField(null=True, blank=True)

    returned_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='returned_cssd_requests'
    )
    returned_at = models.DateTimeField(null=True, blank=True)

    closed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='closed_cssd_requests'
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Request #{self.id} - {self.location.name}"


class CSSDRequestTemplate(models.Model):
    cssd_request = models.ForeignKey(CSSDRequest, on_delete=models.CASCADE, related_name='selected_templates')
    template = models.ForeignKey(CSSDTemplate, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.cssd_request} - {self.template.name}"


class CSSDRequestItem(models.Model):
    cssd_request = models.ForeignKey(
        CSSDRequest,
        on_delete=models.CASCADE,
        related_name='items'
    )

    cssd_request_template = models.ForeignKey(
        CSSDRequestTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_items'
    )

    instrument_name = models.CharField(max_length=150)

    quantity_sent = models.PositiveIntegerField(default=0)
    quantity_received_by_cssd = models.PositiveIntegerField(default=0)
    quantity_returned = models.PositiveIntegerField(default=0)

    remarks = models.TextField(blank=True)
    is_manual = models.BooleanField(default=False)

    def __str__(self):
        return self.instrument_name


class Notification(models.Model):
    TARGET_GROUP_CHOICES = [
        ('MALE', 'Male Clinics'),
        ('FEMALE', 'Female Clinics'),
        ('SPECIALTY', 'Specialty Clinics'),
        ('EMERGENCY', 'Emergency Clinics'),
        ('CSSD', 'CSSD'),
        ('ADMIN', 'Admin'),
    ]

    target_group = models.CharField(max_length=30, choices=TARGET_GROUP_CHOICES)
    title = models.CharField(max_length=150)
    message = models.TextField()
    cssd_request = models.ForeignKey(CSSDRequest, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title