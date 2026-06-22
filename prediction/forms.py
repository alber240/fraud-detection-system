from django import forms

class DatasetUploadForm(forms.Form):
    """Form for uploading CSV/Excel dataset files"""
    
    dataset_file = forms.FileField(
        label='Transaction Dataset',
        help_text='Upload CSV or Excel file with transaction data',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    
    dataset_name = forms.CharField(
        max_length=100,
        required=True,
        label='Dataset Name',
        help_text='Enter a name for this dataset',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., IEEE-CIS Fraud Dataset'
        })
    )
    
    has_header = forms.BooleanField(
        required=False,
        initial=True,
        label='File has header row',
        help_text='Check if the first row contains column names'
    )