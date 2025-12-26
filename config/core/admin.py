from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from .models import *

admin.site.site_header = "KDP MANAGEMENT SYSTEM"

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'view_revenue', 'view_cost', 'view_profit', 'view_roi')
    list_filter = ('status',)
    search_fields = ('title', 'asin')

    # Hiển thị số liệu tài chính đẹp mắt
    def view_revenue(self, obj): return f"{obj.revenue:,.0f} đ"
    def view_cost(self, obj): return f"{(obj.cost_production + obj.cost_ads):,.0f} đ"

    def view_profit(self, obj):
        color = "green" if obj.net_profit > 0 else "red"
        return format_html(f'<b style="color:{color}">{obj.net_profit:,.0f} đ</b>')

    def view_roi(self, obj):
        return f"{obj.roi}%"

    view_revenue.short_description = "Doanh thu"
    view_cost.short_description = "Tổng Chi phí"
    view_profit.short_description = "Lợi nhuận Ròng"
    view_roi.short_description = "ROI"

    # Hiển thị tổng quan Dashboard ở cuối trang danh sách
    def changelist_view(self, request, extra_context=None):
        total_profit = Book.objects.aggregate(
            profit=Sum('revenue') - Sum('cost_production') - Sum('cost_ads')
        )['profit'] or 0
        extra_context = extra_context or {}
        extra_context['subtitle'] = f"TỔNG LỢI NHUẬN TOÀN CÔNG TY: {total_profit:,.0f} VND"
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ProductionTask)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('book', 'template', 'assignee', 'is_completed', 'is_paid', 'preview_cost')
    list_filter = ('is_completed', 'is_paid', 'assignee')

    def preview_cost(self, obj):
        # Demo tính tiền ngay trên giao diện
        return f"{obj.template.standard_hours * 40000:,.0f} đ"
    preview_cost.short_description = "Thành tiền (Dự kiến)"

@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'hours', 'note', 'view_money')

    def view_money(self, obj):
        return f"{obj.hours * 40000:,.0f} đ"
    view_money.short_description = "Lương tạm tính"

# Đăng ký các model khác
admin.site.register(TaskTemplate)
admin.site.register(Transaction)
admin.site.register(SystemConfig)
