from django import forms
from multiupload.fields import MultiFileField
from .models import ProductImage


class ProductImageForm(forms.ModelForm):
    images = MultiFileField(min_num=1, max_num=5, max_file_size=1024*1024*5, 
                           label='Изображения (до 5 шт.)')
    
    class Meta:
        model = ProductImage
        fields = ['images']
    
    def save_files(self, product):
        files = self.cleaned_data.get('images')
        for i, file in enumerate(files):
            # Первое изображение делаем основным
            is_main = (i == 0)
            ProductImage.objects.create(
                product=product,
                image=file,
                is_main=is_main
            )
