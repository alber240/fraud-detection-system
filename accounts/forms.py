from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Customer

class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20)
    address = forms.CharField(widget=forms.Textarea)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    id_number = forms.CharField(max_length=50, label='National ID Number')
    profile_image = forms.ImageField(required=False, label='Profile Picture')  # extra field

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'phone', 'address', 'date_of_birth', 'id_number')
        # profile_image is not included here

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create customer with all fields, including profile_image
            customer = Customer(
                user=user,
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address'],
                date_of_birth=self.cleaned_data['date_of_birth'],
                id_number=self.cleaned_data['id_number'],
                profile_image=self.cleaned_data.get('profile_image'),
            )
            customer.save()
        return user