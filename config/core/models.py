from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

# --- 1. CẤU HÌNH LƯƠNG & TỶ GIÁ ---
class SystemConfig(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.IntegerField(default=40000) # Mặc định 40k/giờ

    def __str__(self): return f"{self.key}: {self.value}"

# --- 2. SÁCH (SẢN PHẨM) ---
class Book(models.Model):
    STATUS_CHOICES = [('WRITING', 'Đang viết'), ('DESIGN', 'Đang thiết kế'), ('LIVE', 'Đang bán')]

    title = models.CharField("Tên sách", max_length=200)
    asin = models.CharField("ASIN", max_length=20, unique=True, null=True, blank=True)
    status = models.CharField(choices=STATUS_CHOICES, default='WRITING', max_length=20)

    # Tài chính (Tự động tính)
    revenue = models.DecimalField("Doanh thu Royalty (VND)", max_digits=15, decimal_places=0, default=0)
    cost_production = models.DecimalField("Chi phí SX (VND)", max_digits=15, decimal_places=0, default=0)
    cost_ads = models.DecimalField("Chi phí Ads (VND)", max_digits=15, decimal_places=0, default=0)

    @property
    def net_profit(self):
        return self.revenue - (self.cost_production + self.cost_ads)

    @property
    def roi(self):
        total_cost = self.cost_production + self.cost_ads
        if total_cost == 0: return 0
        return round((self.net_profit / total_cost) * 100, 2)

    def __str__(self): return self.title

# --- 3. QUẢN LÝ TASK (TEAM SẢN XUẤT - LƯƠNG KHOÁN) ---
class TaskTemplate(models.Model):
    name = models.CharField("Tên công việc", max_length=100) # VD: Viết outline
    standard_hours = models.DecimalField("Định mức giờ", max_digits=5, decimal_places=1) # VD: 16h

    def __str__(self): return f"{self.name} ({self.standard_hours}h)"

class ProductionTask(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    template = models.ForeignKey(TaskTemplate, on_delete=models.PROTECT)
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Người làm")
    is_completed = models.BooleanField("Đã xong", default=False)
    is_paid = models.BooleanField("Đã trả lương", default=False)

    def save(self, *args, **kwargs):
        # AUTOMATION: Khi đánh dấu "Đã trả lương", tự cộng tiền vào chi phí Sách
        if self.is_paid:
            rate = SystemConfig.objects.get_or_create(key="HOURLY_RATE", defaults={'value': 40000})[0].value
            cost = self.template.standard_hours * rate

            # Tạo Transaction tự động (Simplified logic)
            Transaction.objects.create(
                book=self.book,
                amount=cost,
                type='COST_PRODUCTION',
                note=f"Lương {self.assignee} - {self.template.name}"
            )
        super().save(*args, **kwargs)

# --- 4. CHẤM CÔNG (TEAM MARKETING - LƯƠNG GIỜ) ---
class TimeLog(models.Model):
    staff = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    hours = models.DecimalField("Số giờ làm", max_digits=4, decimal_places=1)
    note = models.TextField("Mô tả CV")
    is_verified = models.BooleanField("Duyệt", default=False)

    @property
    def estimated_earnings(self):
        rate = SystemConfig.objects.get_or_create(key="HOURLY_RATE", defaults={'value': 40000})[0].value
        return self.hours * rate

# --- 5. DÒNG TIỀN (SỔ CÁI) ---
class Transaction(models.Model):
    TYPES = [('REVENUE', 'Doanh thu'), ('COST_PRODUCTION', 'Chi phí SX'), ('COST_ADS', 'Chi phí Ads')]
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField("Số tiền (VND)", max_digits=15, decimal_places=0)
    type = models.CharField(choices=TYPES, max_length=50)
    date = models.DateField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # AUTOMATION: Cập nhật tổng tiền vào Sách mỗi khi có Transaction mới
        if self.book:
            if self.type == 'REVENUE':
                self.book.revenue = Transaction.objects.filter(book=self.book, type='REVENUE').aggregate(Sum('amount'))['amount__sum'] or 0
            elif self.type == 'COST_PRODUCTION':
                self.book.cost_production = Transaction.objects.filter(book=self.book, type='COST_PRODUCTION').aggregate(Sum('amount'))['amount__sum'] or 0
            elif self.type == 'COST_ADS':
                self.book.cost_ads = Transaction.objects.filter(book=self.book, type='COST_ADS').aggregate(Sum('amount'))['amount__sum'] or 0
            self.book.save()
