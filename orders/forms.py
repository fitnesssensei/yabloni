from django import forms
from .models import Order

class OrderCreateForm(forms.ModelForm):
    full_name = forms.CharField(
        label='Покупатель',
        max_length=160,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия Имя Отчество'
        })
    )
    
    class Meta:
        model = Order
        fields = ['full_name', 'email', 'phone', 'delivery_needed', 'region', 'city', 'postal_code', 'address', 'comments']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '+7 (XXX) XXX-XX-XX',
                'pattern': r'^(\+7|8)?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$',
                'title': 'Формат: +7 (XXX) XXX-XX-XX или 8XXXXXXXXXX'
            }),
            'delivery_needed': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'style': 'width: 20px; height: 20px;'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Улица, дом, этаж, квартира'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Почтовый индекс'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Город'
            }),
            'region': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Страна, край, район'
            }),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Комментарий к заказу (необязательно)',
                'rows': 4
            }),
            
        }
    
    def clean_phone(self):
        """Дополнительная очистка и валидация телефонного номера"""
        phone = self.cleaned_data['phone']
        
        # Удаляем все символы кроме цифр и плюса
        cleaned_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Если номер начинается с 8, заменяем на +7
        if cleaned_phone.startswith('8'):
            cleaned_phone = '+7' + cleaned_phone[1:]
        elif cleaned_phone.startswith('7') and not cleaned_phone.startswith('+7'):
            cleaned_phone = '+7' + cleaned_phone[1:]
        elif not cleaned_phone.startswith('+7'):
            cleaned_phone = '+7' + cleaned_phone
        
        return cleaned_phone
    
    def clean_full_name(self):
        """Разделяем полное ФИО на фамилию, имя и отчество"""
        full_name = self.cleaned_data['full_name'].strip()
        
        if not full_name:
            raise forms.ValidationError('Введите ФИО')
        
        parts = full_name.split()
        if len(parts) < 2:
            raise forms.ValidationError('Введите как минимум фамилию и имя')
        
        # Сохраняем части для последующего использования
        self.cleaned_data['_last_name'] = parts[0]
        self.cleaned_data['_first_name'] = parts[1]
        self.cleaned_data['_patronymic'] = ' '.join(parts[2:]) if len(parts) > 2 else ''
        
        return full_name

    def save(self, commit=True):
        """Переопределяем сохранение для разделения ФИО"""
        instance = super().save(commit=False)
        
        # Устанавливаем разделенные значения
        instance.last_name = self.cleaned_data['_last_name']
        instance.first_name = self.cleaned_data['_first_name']
        instance.patronymic = self.cleaned_data['_patronymic']
        
        if commit:
            instance.save()
        return instance