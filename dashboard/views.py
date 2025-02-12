import hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .forms import *
from .models import Dataset
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect  
from statsmodels.tsa.arima.model import ARIMA  
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, FileResponse
import os
import pdfkit
from .forms import *
from django.template.loader import render_to_string
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
import base64
from django.contrib.auth.forms import UserChangeForm
from io import BytesIO
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from datetime import datetime
import re
from django.db.models import Q
from django.http import JsonResponse    
from django.core.paginator import Paginator


# Registration View
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('login')  # Make sure 'login' is the correct URL name
        else:
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = RegistrationForm()
    
    return render(request, 'register.html', {'form': form})

# Login View
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            print(f"User authenticated: {user}")  # Debugging line
            if user is not None:
                login(request, user)
                print("Login successful, redirecting to dashboard.")  # Debugging line
                return redirect('upload_and_visualize')  # Ensure the URL name is correct
            else:
                messages.error(request, "Invalid username or password")
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()  # Initialize form for GET request
    return render(request, 'login.html', {'form': form})

# Logout View
@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('landing')

# Forgot Password View
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)

            # Construct the reset password URL
            reset_url = request.build_absolute_uri('/reset-password/')  # No token required

            # Send password reset email
            send_mail(
                'Password Reset Request',
                f'Click the link to reset your password: {reset_url}',
                'admin@yourdomain.com',
                [email],
            )

            messages.success(request, 'A password reset link has been sent to your email.')
            return redirect('forgot_password')
        except User.DoesNotExist:
            messages.error(request, 'No user with this email exists.')

    return render(request, 'forgot_password.html')

# Reset Password View
def reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        try:
            user = User.objects.get(email=email)
            if new_password == confirm_password:
                user.password = make_password(new_password)
                user.save()
                messages.success(request, 'Your password has been reset successfully.')
                return redirect('password_reset_success')
            else:
                messages.error(request, 'Passwords do not match.')
        except User.DoesNotExist:
            messages.error(request, 'No user with this email exists.')

    return render(request, 'reset_password.html')

# Password Reset Success View
def password_reset_success(request):
    return render(request, 'password_reset_success.html')


def landing_view(request):
    return render(request, 'landing.html')




import zipfile
import os
from django.http import HttpResponse
from .models import Dataset
from django.core.paginator import Paginator

import requests
from django.http import HttpResponseRedirect

def upload(request):
    # Define all required fields for validation
    REQUIRED_FIELDS = ["Region", "Date", "Total_Sales", "Order_ID", "Product_Size", "Material", "Sales_Channel", "Quantity_Sold", "Unit_Price"]

    def normalize_column(column):
        """Normalize column names for consistent comparison."""
        return column.strip().lower().replace(" ", "_").replace("-", "_")

    # Fetch the upload history for the logged-in user
    upload_history = Dataset.objects.filter(user=request.user).order_by('-uploaded_at')

    # Handle the filter form for portfolio functionality
    filter_form = DatasetFilterForm(request.GET)
    if filter_form.is_valid():
        file_name = filter_form.cleaned_data['file_name']
        start_date = filter_form.cleaned_data['start_date']
        end_date = filter_form.cleaned_data['end_date']
        # Apply filters based on form input
        if file_name:
            upload_history = upload_history.filter(file__icontains=file_name)
        if start_date:
            upload_history = upload_history.filter(uploaded_at__date__gte=start_date)
        if end_date:
            upload_history = upload_history.filter(uploaded_at__date__lte=end_date)

    # Add pagination
    paginator = Paginator(upload_history, 10)  # Show 10 datasets per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Add a flag to indicate if pagination should be shown
    show_pagination = upload_history.count() > 10  

    if request.method == "POST":
        if 'download_all' in request.POST:
            # Create a ZIP file in memory
            response = HttpResponse(content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="All_datasets.zip"'

            with zipfile.ZipFile(response, 'w') as zipf:
                for dataset in upload_history:
                    file_path = dataset.file.path
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))

            return response

        form = DatasetUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES['file']
            file_hash = hashlib.sha256(uploaded_file.read()).hexdigest()
            uploaded_file.seek(0)

            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file)
                else:
                    messages.error(request, "Unsupported file format. Please upload a CSV or Excel file.")
                    return redirect('upload')
            except Exception as e:
                messages.error(request, f"Error reading file: {e}")
                return redirect('upload')

            uploaded_columns = {normalize_column(col) for col in df.columns}
            required_fields_normalized = {normalize_column(field) for field in REQUIRED_FIELDS}
            missing_fields = required_fields_normalized - uploaded_columns
            if missing_fields:
                messages.error(request, f"The file is missing required fields: {', '.join(missing_fields)}.")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/upload/'))

            # Data validation for required columns
            validation_errors = []

            # Validate each required column
            for column in REQUIRED_FIELDS:
                normalized_column = normalize_column(column)
                if normalized_column in uploaded_columns:
                    if column == "Date":
                        # Ensure all values are valid dates
                        df[column] = pd.to_datetime(df[column], errors='coerce')
                        if df[column].isnull().any():
                            validation_errors.append(f"The '{column}' column contains invalid date values.")
                    elif column == "Total_Sales":
                        # Ensure the column has only numerical values
                        if not pd.api.types.is_numeric_dtype(df[column]):
                            validation_errors.append(f"The '{column}' column must contain only numerical values.")
                    elif column == "Quantity_Sold":
                        # Ensure the column has only numerical values
                        if not pd.api.types.is_numeric_dtype(df[column]):
                            validation_errors.append(f"The '{column}' column must contain only numerical values.")
                    elif column == "Unit_Price":
                        # Ensure the column has only numerical values
                        if not pd.api.types.is_numeric_dtype(df[column]):
                            validation_errors.append(f"The '{column}' column must contain only numerical values.")
                    elif column == "Order_ID":
                        # Ensure the 'Order_ID' column matches the format ORD-1000
                        if not df[column].apply(lambda x: isinstance(x, str) and x.startswith('ORD-') and x[4:].isdigit()).all():
                            validation_errors.append(f"The '{column}' column must contain valid order IDs in the format 'ORD-1000'.")
                    elif column == "Product_Size":
                        # Check if the 'Product_Size' column has valid product sizes
                        valid_sizes = ["Extra Large", "Large", "Medium", "Small", "Mini", "Compact", "Standard", "Oversized", "Custom"]
                        if not df[column].isin(valid_sizes).all():
                            validation_errors.append(f"The '{column}' column must contain only valid product sizes: {', '.join(valid_sizes)}.")
                    elif column == "Material":
                        # Check if the 'Material' column has valid material types
                        valid_materials = ["Acrylic", "Polycarbonate", "Glass", "Fiberglass", "Metal", "PVC", "Wood", "Polyvinyl butyral (PVB)", "Composite materials", "Solar panels"]
                        if not df[column].isin(valid_materials).all():
                            validation_errors.append(f"The '{column}' column must contain only valid materials: {', '.join(valid_materials)}.")
                    elif column == "Sales_Channel":
                        # Check if the 'Sales_Channel' column has valid sales channels
                        valid_channels = ["Distributor", "Online", "Retail", "Wholesaler", "Direct", "Agent", "Franchise", "E-commerce", "Showroom"]
                        if not df[column].isin(valid_channels).all():
                            validation_errors.append(f"The '{column}' column must contain only valid sales channels: {', '.join(valid_channels)}.")
                    elif column == "Region":
                        # Ensure the 'Region' column only contains strings
                          if not df[column].apply(lambda x: isinstance(x, str) and all(char.isalpha() or char.isspace() or char == '-' or char == '_' for char in x)).all():
                            validation_errors.append(f"The '{column}' column must contain only string values.")

            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/upload/'))

            dataset = Dataset.objects.filter(file_hash=file_hash).first()
            if dataset is None:
                dataset = form.save(commit=False)
                dataset.file_hash = file_hash
                dataset.user = request.user
                dataset.save()

            return redirect('visualize_dataset', dataset_id=dataset.id)

    else:
        form = DatasetUploadForm()

    return render(request, 'upload.html', {
        'form': form,
        'upload_history': page_obj,
        'filter_form': filter_form,
        'show_pagination': show_pagination,  # Pass the flag to the template
    })





# View to return dataset rows for a given dataset
def get_dataset_rows(request, dataset_id):
    dataset = get_object_or_404(Dataset, id=dataset_id)
    file_path = dataset.file.path

    # Read CSV or XLSX based on the file extension
    try:
        if file_path.endswith('.csv'):
            data = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            data = pd.read_excel(file_path, engine='openpyxl')
        else:
            return JsonResponse({'error': 'Unsupported file format'}, status=400)

        # Get column headers from the dataframe
        headers = list(data.columns)

        # Convert the dataframe rows into a list of lists
        rows = data.values.tolist()

        return JsonResponse({'headers': headers, 'rows': rows})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def visualize(request, dataset_id):
    # Retrieve the dataset from the database
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        messages.error(request, "Dataset not found!")
        return HttpResponseRedirect('/upload/')

    file_path = dataset.file.path

    # Required columns for visualization
    required_columns = ["Region", "Date", "Total_Sales", "Order_ID", "Product_Size", "Material", "Sales_Channel", "Quantity_Sold"]

    try:
        # Check file extension and read the appropriate file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.xls') or file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            messages.error(request, "Unsupported file format. Please upload CSV or Excel files.")
            return HttpResponseRedirect('/upload/')

        # Normalize columns to handle case insensitivity and underscores
        df.columns = [re.sub(r'[\s_]+', '_', col.strip().lower()) for col in df.columns]
        normalized_required_columns = [re.sub(r'[\s_]+', '_', col.lower()) for col in required_columns]

        # Check if required columns are present
        available_columns = [col for col in normalized_required_columns if col in df.columns]
        missing_columns = [col for col in normalized_required_columns if col not in df.columns]

        if not available_columns:
            # Case 1: No required columns found
            messages.error(
                request,
                f"The uploaded dataset does not contain any required columns: {', '.join(required_columns)}."
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/upload/'))

        if missing_columns:
            # Case 3: Some required columns are missing
            messages.warning(
                request,
                f"The following columns are missing and will not be included in the visualizations: {', '.join(missing_columns)}."
            )

        # Rename DataFrame columns to match normalized required column names
        column_mapping = dict(zip(normalized_required_columns, required_columns))
        df.rename(columns={col: column_mapping[col] for col in available_columns}, inplace=True)

        # Preprocess DataFrame
        if "Date" in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')  # Ensure dates are parsed
            if df['Date'].isnull().any():
                messages.error(request, "Invalid date format in the dataset.")
                return HttpResponseRedirect('/upload/')
            df['Month'] = df['Date'].dt.to_period('M').astype(str)

        # KPI Calculations
        total_regions = df["Region"].nunique() if "Region" in df.columns else None
        total_product_sizes = df["Product_Size"].nunique() if "Product_Size" in df.columns else None
        total_sales = df["Total_Sales"].sum() if "Total_Sales" in df.columns else None
        total_orders = df["Order_ID"].nunique() if "Order_ID" in df.columns else None

        # Generate visualizations based on available columns
        charts = {}

        if "Month" in df.columns and "Region" in df.columns and "Total_Sales" in df.columns:
            charts['chart1'] = px.area(
                df.groupby(['Month', 'Region'])['Total_Sales'].sum().reset_index(),
                x="Month", y="Total_Sales", color="Region",
                title="Monthly Sales by Region",
                color_discrete_sequence=px.colors.qualitative.Set2
            ).to_html(full_html=False)

        if "Product_Size" in df.columns and "Total_Sales" in df.columns:
            charts['chart2'] = px.bar(
                df, x="Product_Size", y="Total_Sales", title="Total Sales by Product Size",
                color="Product_Size", color_discrete_sequence=px.colors.qualitative.Dark2
            ).to_html(full_html=False)

        if "Material" in df.columns and "Total_Sales" in df.columns:
            charts['chart3'] = px.pie(
                df, names="Material", values="Total_Sales",
                title="Sales by Material",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                hole=0.3
            ).to_html(full_html=False)

        if "Region" in df.columns and "Sales_Channel" in df.columns and "Total_Sales" in df.columns:
            charts['chart4'] = px.bar(
                df, x="Region", y="Total_Sales", color="Sales_Channel",
                title="Sales by Region and Channel", barmode="group", color_discrete_sequence=px.colors.qualitative.Prism
            ).to_html(full_html=False)

        if "Quantity_Sold" in df.columns and "Total_Sales" in df.columns and "Product_Size" in df.columns:
            charts['chart5'] = px.scatter(
                df, x="Quantity_Sold", y="Total_Sales", color="Product_Size",
                title="Quantity Sold vs. Total Sales by Product Size",
                color_discrete_sequence=px.colors.qualitative.Set3
            ).to_html(full_html=False)

        if "Month" in df.columns and "Region" in df.columns:
            heatmap_data = df.groupby(['Month', 'Region'])['Total_Sales'].sum().unstack().fillna(0)
            charts['chart6'] = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale="Viridis"
            ))
            charts['chart6'].update_layout(title="Sales Density by Region and Month")
            charts['chart6'] = charts['chart6'].to_html(full_html=False)

        if "Sales_Channel" in df.columns:
            sales_by_channel = df.groupby("Sales_Channel")["Total_Sales"].sum().reset_index()
            charts['chart7'] = go.Figure(data=[go.Pie(
                labels=sales_by_channel["Sales_Channel"], values=sales_by_channel["Total_Sales"],
                title="Sales by Sales Channel", hole=0.5
            )])
            charts['chart7'] = charts['chart7'].to_html(full_html=False)

        if "Total_Sales" in df.columns:
            sales_goal = 100000
            charts['chart8'] = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=total_sales,
                title={'text': "Total Sales Goal Achievement"},
                gauge={'axis': {'range': [None, sales_goal]}, 'bar': {'color': "darkblue"}},
                delta={'reference': sales_goal * 0.75}
            ))
            charts['chart8'] = charts['chart8'].to_html(full_html=False)

        # Sales Forecasting
        if "Date" in df.columns and "Total_Sales" in df.columns:
            df.set_index('Date', inplace=True)
            monthly_sales_total = df.resample('M')['Total_Sales'].sum()

            # ARIMA model for forecasting
            model = ARIMA(monthly_sales_total, order=(1, 1, 1))
            model_fit = model.fit()
            forecast = model_fit.forecast(steps=6)
            forecast_dates = pd.date_range(monthly_sales_total.index[-1] + pd.DateOffset(1), periods=6, freq='M')
            forecast_series = pd.Series(forecast, index=forecast_dates)

            # Combine actual and forecasted data
            combined_sales = pd.concat([monthly_sales_total, forecast_series])

            # Plot forecast
            fig_forecast = go.Figure()
            fig_forecast.add_trace(go.Scatter(
                x=monthly_sales_total.index, y=monthly_sales_total, mode='lines+markers', name='Actual Sales'
            ))
            fig_forecast.add_trace(go.Scatter(
                x=forecast_series.index, y=forecast_series, mode='lines+markers', name='Forecasted Sales', line=dict(dash='dash')
            ))
            fig_forecast.update_layout(title="Sales Forecast for Next 6 Months")
            charts['forecast_chart'] = fig_forecast.to_html(full_html=False)

        # Mapbox visualization (8th chart)
        if "Region" in df.columns and "Total_Sales" in df.columns:
    # Define region coordinates
            region_coordinates = {
                'Europe': {'lat': 54.5260, 'lon': 15.2551},
                'Asia-Pacific': {'lat': -8.7832, 'lon': 124.5085},
                'North America': {'lat': 54.5260, 'lon': -105.2551},
                'Middle East': {'lat': 25.276987, 'lon': 55.296249},
                'South America': {'lat': -14.2350, 'lon': -51.9253},
                'Africa': {'lat': 1.6508, 'lon': 10.2679},
                'India': {'lat': 20.5937, 'lon': 78.9629} , # Add India explicitly
                'Central': {'lat': 14.6048, 'lon': -90.4892},  # Example: Guatemala City, Central America
                'East': {'lat': 35.6895, 'lon': 139.6917},  # Example: Tokyo, Japan, East Asia
                'North': {'lat': 78.2232, 'lon': 15.6469},  # Example: Svalbard, Norway, Northern Hemisphere
                'South': {'lat': -33.9249, 'lon': 18.4241},  # Example: Cape Town, South Africa
                'West': {'lat': 37.7749, 'lon': -122.4194}  # Example: San Francisco, USA, Western Hemisphere
            }

            # Group sales by region
            sales_by_region = df.groupby('Region')['Total_Sales'].sum().reset_index()

            # Map latitude and longitude based on region
            sales_by_region['Latitude'] = sales_by_region['Region'].map(lambda x: region_coordinates.get(x, {}).get('lat'))
            sales_by_region['Longitude'] = sales_by_region['Region'].map(lambda x: region_coordinates.get(x, {}).get('lon'))

            # Check if any regions are missing coordinates
            missing_regions = sales_by_region[sales_by_region[['Latitude', 'Longitude']].isnull().any(axis=1)]
            if not missing_regions.empty:
                print(f"Warning: The following regions have no matching coordinates: {missing_regions['Region'].tolist()}")
            else:
                # Create the map with OpenStreetMap style
                fig_mapbox = px.scatter_mapbox(
                    sales_by_region,
                    lat='Latitude',
                    lon='Longitude',
                    size='Total_Sales',
                    color='Total_Sales',
                    hover_name='Region',
                    title='Regional Sales Distribution',
                    color_continuous_scale='Viridis',
                    mapbox_style='open-street-map'  # Use OpenStreetMap style
                )

                # Update map layout to center on India and set zoom level
                fig_mapbox.update_layout(
                    mapbox=dict(
                        center={"lat": 20.5937, "lon": 78.9629},  # Center on India
                        zoom=4,  # Adjust this value for zoom level
                        style="open-street-map"
                    )
                )

                # Add the map to the charts dictionary
                charts['mapbox'] = fig_mapbox.to_html(full_html=False)

        # Render the dashboard with charts and KPIs
        context = {
            'dataset': dataset,
            'total_regions': total_regions,
            'dataset_name': dataset.file,
            'total_product_sizes': total_product_sizes,
            'total_sales': total_sales,
            'total_orders': total_orders,
            'charts': charts,
        }

        return render(request, 'dashboard.html', context)

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return HttpResponseRedirect('/upload/')


def clear_dataset(request, dataset_id):
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        dataset.delete()
        messages.success(request, "Dataset deleted successfully!")
    except Dataset.DoesNotExist:
        messages.error(request, "Dataset not found!")

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/upload/'))





def download_dataset(request, dataset_id):
    dataset = get_object_or_404(Dataset, id=dataset_id)  # Replace with your model
    
    try:
        # Get the original file name without the path
        original_name = dataset.file.name.split('/')[-1]
        
        # Format current date as desired, e.g., "YYYY-MM-DD"
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Append date to the original file name
        filename = f"{current_date}_{original_name}"
        
        response = FileResponse(dataset.file.open('rb'), as_attachment=True, filename=filename)
        
        # Add success message
        messages.success(request, "Dataset downloaded successfully!")
        
        return response
    except FileNotFoundError:
        raise Http404("File not found")


def compare_existing_sales(request, dataset_id):
    # Get the dataset selected for comparison (previous month)
    previous_month_data = get_object_or_404(Dataset, id=dataset_id)

    # Retrieve the dataset to compare with, from the 'compare_with' GET parameter
    compare_with_id = request.GET.get('compare_with')
    if not compare_with_id:
        return HttpResponseBadRequest("No dataset selected for comparison.")

    # Get the current month's dataset for comparison
    current_month_data = get_object_or_404(Dataset, id=compare_with_id)

    # Load the CSV data of both datasets
    try:
        previous_month_df = pd.read_csv(previous_month_data.file.path)
        current_month_df = pd.read_csv(current_month_data.file.path)
    except Exception as e:
        return HttpResponseBadRequest(f"Error loading CSV files: {e}")

    # Ensure 'Date' columns are in datetime format if they exist
    for df in [previous_month_df, current_month_df]:
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')  # 'coerce' converts errors to NaT

    # Calculate total sales by Product Size for both months
    current_month_sales = current_month_df.groupby('Product_Size')['Total_Sales'].sum().reset_index()
    previous_month_sales = previous_month_df.groupby('Product_Size')['Total_Sales'].sum().reset_index()

    # Merge the two DataFrames for comparison
    comparison_df = pd.merge(
        current_month_sales, previous_month_sales, 
        on='Product_Size', how='outer', suffixes=('_current', '_previous')
    )
    comparison_df.fillna(0, inplace=True)  # Replace NaNs with zeros

    # Calculate the sales difference
    comparison_df['Sales_Difference'] = comparison_df['Total_Sales_current'] - comparison_df['Total_Sales_previous']

    # Generate bar charts for total sales and sales difference
    fig = px.bar(
        comparison_df, 
        x='Product_Size', 
        y=['Total_Sales_current', 'Total_Sales_previous'],
        title="Sales Comparison: Current Month vs. Previous Month",
        labels={'value': 'Total Sales', 'variable': 'Month'},
        barmode='group'
    )

    fig_diff = px.bar(
        comparison_df, 
        x='Product_Size', 
        y='Sales_Difference',
        title="Sales Difference (Current Month - Previous Month)",
        labels={'value': 'Sales Difference'},
        color='Sales_Difference',
        color_continuous_scale='RdBu'
    )

    # Convert figures to HTML
    fig_html = fig.to_html(full_html=False)
    fig_diff_html = fig_diff.to_html(full_html=False)

    # Prepare context for the template
    context = {
        'fig_html': fig_html,
        'fig_diff_html': fig_diff_html,
        'comparison_df': comparison_df.to_html(classes='table table-striped', index=False),
        'previous_month_data': previous_month_data,
        'current_month_data': current_month_data,
    }

    return render(request, 'existing_sales_comparison.html', context)



def compare_sales(request, dataset_id=None):
    REQUIRED_COLUMNS = [
        "Region", "Date", "Total_Sales", "Order_ID", 
        "Product_Size", "Material", "Sales_Channel", "Quantity_Sold","Unit_Price"
    ]

    previous_month_df = None
    previous_month_data = None

    # Fetch the previous month's data if dataset_id is provided
    if dataset_id:
        previous_month_data = get_object_or_404(Dataset, id=dataset_id)
        previous_month_file = previous_month_data.file.path
        if previous_month_file.endswith(('.xls', '.xlsx')):
            previous_month_df = pd.read_excel(previous_month_file)
        elif previous_month_file.endswith('.csv'):
            previous_month_df = pd.read_csv(previous_month_file)
        else:
            return render(request, 'sales_comparison.html', {
                'error_message': "Unsupported file format for the previous month's data."
            })

    # Handle form submission on POST request
    if request.method == 'POST':
        form = SalesComparisonForm(request.POST, request.FILES)

        if form.is_valid() and 'current_month_file' in request.FILES:
            current_month_file = request.FILES['current_month_file']
            file_extension = current_month_file.name.split('.')[-1].lower()

            # Read file based on its format
            if file_extension in ['xls', 'xlsx']:
                current_month_df = pd.read_excel(current_month_file)
            elif file_extension == 'csv':
                current_month_df = pd.read_csv(current_month_file)
            else:
                return render(request, 'sales_comparison.html', {
                    'form': form,
                    'error_message': "Unsupported file format for the current month's data."
                })

            # Check if all required columns are present in the current month's data
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in current_month_df.columns]
            if missing_columns:
                return render(request, 'sales_comparison.html', {
                    'form': form,
                    'error_message': f"Missing required columns in the uploaded data: {', '.join(missing_columns)}"
                })

            # Calculate file hash for uniqueness check
            current_month_file.seek(0)  # Ensure we start from the beginning of the file
            file_hash = hashlib.sha256(current_month_file.read()).hexdigest()
            current_month_file.seek(0)  # Reset the file pointer after reading

            # Check if the dataset with this hash already exists
            existing_dataset = Dataset.objects.filter(file_hash=file_hash).first()

            if existing_dataset:
                # If the dataset exists, simply assign the existing dataset's file
                current_month_dataset = existing_dataset
            else:
                # Save the new dataset and link it to the previous one
                current_month_dataset = Dataset(
                    file=current_month_file,
                    file_hash=file_hash,
                    user=request.user,
                    compare_with=previous_month_data
                )
                current_month_dataset.save()  # Save only if it's a new dataset

            # Proceed with comparison if the previous month's data is available
            if previous_month_df is not None:
                # Ensure the 'Date' column is in datetime format
                current_month_df['Date'] = pd.to_datetime(current_month_df['Date'], errors='coerce')
                previous_month_df['Date'] = pd.to_datetime(previous_month_df['Date'], errors='coerce')

                # Group by 'Product_Size' and sum 'Total_Sales'
                current_month_sales = current_month_df.groupby('Product_Size')['Total_Sales'].sum().reset_index()
                previous_month_sales = previous_month_df.groupby('Product_Size')['Total_Sales'].sum().reset_index()

                # Merge current and previous month sales data
                comparison_df = pd.merge(
                    current_month_sales, previous_month_sales,
                    on='Product_Size', how='outer', suffixes=('_current', '_previous')
                )
                comparison_df.fillna(0, inplace=True)
                comparison_df['Sales_Difference'] = comparison_df['Total_Sales_current'] - comparison_df['Total_Sales_previous']

                # Create bar charts using Plotly
                fig = px.bar(
                    comparison_df, x='Product_Size',
                    y=['Total_Sales_current', 'Total_Sales_previous'],
                    title="Sales Comparison: Current Month vs. Previous Month",
                    labels={'value': 'Total Sales', 'variable': 'Month'},
                    barmode='group'
                )

                fig_diff = px.bar(
                    comparison_df, x='Product_Size', y='Sales_Difference',
                    title="Sales Difference (Current Month - Previous Month)",
                    labels={'value': 'Sales Difference'},
                    color='Sales_Difference',
                    color_continuous_scale='RdBu'
                )

                # Convert Plotly figures to HTML
                fig_html = fig.to_html(full_html=False)
                fig_diff_html = fig_diff.to_html(full_html=False)

                # Prepare context for rendering the template
                context = {
                    'form': SalesComparisonForm(),
                    'fig_html': fig_html,
                    'fig_diff_html': fig_diff_html,
                    'comparison_df': comparison_df.to_html(classes='table table-striped', index=False),
                    'previous_month_data': previous_month_data,
                    'current_month_data': current_month_dataset,
                }
                return render(request, 'sales_comparison.html', context)

            else:
                # If there's no previous month's data, notify the user
                context = {
                    'form': form,
                    'error_message': "No previous month's data available for comparison.",
                }
                return render(request, 'sales_comparison.html', context)

    # Initial GET request: Display the form
    else:
        form = SalesComparisonForm()
        context = {
            'form': form,
            'dataset_id': dataset_id,
            'previous_month_data': previous_month_data
        }
        return render(request, 'sales_comparison.html', context)



import chardet

def detect_file_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read(1024)  # Read a small part of the file
    result = chardet.detect(raw_data)
    return result['encoding']


def visualize_comparison(request, dataset_id):
    # Fetch the primary dataset and its comparison dataset
    primary_dataset = get_object_or_404(Dataset, id=dataset_id)
    comparison_dataset = primary_dataset.compare_with

    def load_dataset(file_path):
        # Detect file format by extension
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Detect encoding for CSV files
        if file_extension == '.csv':
            encoding = detect_file_encoding(file_path)
            return pd.read_csv(file_path, encoding=encoding)
        elif file_extension in ['.xls', '.xlsx']:
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

    # Load data for the primary dataset
    primary_df = load_dataset(primary_dataset.file.path)

    # Check if a comparison dataset exists and load its data
    comparison_df = None
    if comparison_dataset:
        comparison_df = load_dataset(comparison_dataset.file.path)

    # Prepare visualizations
    fig_primary = px.bar(
        primary_df, x='Product_Size', y='Total_Sales',
        title="Primary Dataset - Total Sales by Product Size",
        labels={'Total_Sales': 'Total Sales', 'Product_Size': 'Product Size'}
    )

    fig_comparison = None
    if comparison_df is not None and not comparison_df.empty:  # Ensure the comparison DataFrame isn't empty
        fig_comparison = px.bar(
            comparison_df, x='Product_Size', y='Total_Sales',
            title="Comparison Dataset - Total Sales by Product Size",
            labels={'Total_Sales': 'Total Sales', 'Product_Size': 'Product Size'}
        )

    # Convert figures to HTML
    fig_primary_html = fig_primary.to_html(full_html=False)
    fig_comparison_html = fig_comparison.to_html(full_html=False) if fig_comparison else None

    # Prepare the comparison table
    comparison_table = []
    if comparison_df is not None and not comparison_df.empty:
        # Group by Product_Size and sum the Total_Sales
        primary_grouped = primary_df.groupby('Product_Size')['Total_Sales'].sum()
        comparison_grouped = comparison_df.groupby('Product_Size')['Total_Sales'].sum()

        # Iterate over primary sales data
        for product_size, primary_sales in primary_grouped.items():
            comparison_sales = comparison_grouped.get(product_size, 0)  # Use 0 if no match in comparison data
            sales_difference = primary_sales - comparison_sales

            comparison_table.append({
                'Product_Size': product_size,
                'Total_Sales_primary': primary_sales,
                'Total_Sales_comparison': comparison_sales,
                'Sales_Difference': sales_difference
            })

    # Context to pass to template
    context = {
        'primary_dataset': primary_dataset,
        'comparison_dataset': comparison_dataset,
        'fig_primary_html': fig_primary_html,
        'fig_comparison_html': fig_comparison_html,
        'comparison_table': comparison_table,
    }
    
    return render(request, 'dataset_visualization.html', context)



@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('profile')  # Redirect back to the profile page or wherever you'd like
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserChangeForm(instance=request.user)

    return render(request, 'upload.html', {'form': form})

def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)  # Keeps the user logged in after password change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('upload_and_visualize')  # Redirect to profile or another page
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'upload.html', {'form': form})




import json
from statsmodels.tsa.arima.model import ARIMA
from sklearn.linear_model import LinearRegression
import numpy as np


def standardize_column_name(column):
    return column.strip().lower().replace(" ", "_").replace("-", "_")

def upload_and_predict(request):
    if request.method == 'POST':
        form = SalesDataUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES['file']
            uploaded_file_name = uploaded_file.name  # Capture the name of the uploaded file

            try:
                # Detect file type
                if uploaded_file.name.endswith('.csv'):
                    sales_data = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith(('.xls', '.xlsx')):
                    sales_data = pd.read_excel(uploaded_file)
                else:
                    messages.error(request, "Unsupported file format. Please upload a CSV or Excel file.")
                    return render(request, 'upload.html', {'form': form})

                # Normalize column names
                sales_data.columns = [standardize_column_name(col) for col in sales_data.columns]

                # Map column names
                column_mapping = {
                    'date': ['date', 'datetime', 'timestamp', 'day'],
                    'total_sales': ['total_sales', 'sales', 'revenue', 'sale', 'income', 'turnover']
                }
                for standard_col, possible_names in column_mapping.items():
                    for name in possible_names:
                        if name in sales_data.columns:
                            sales_data.rename(columns={name: standard_col}, inplace=True)
                            break

                if 'date' not in sales_data.columns or 'total_sales' not in sales_data.columns:
                    messages.error(request, "Required columns ('date', 'total_sales') are missing.")
                    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/upload/'))

                # Convert 'date' to datetime and clean data
                sales_data['date'] = pd.to_datetime(sales_data['date'], errors='coerce')
                sales_data.dropna(subset=['date'], inplace=True)
                sales_data.set_index('date', inplace=True)
                sales_data = sales_data.sort_index()
                monthly_sales = sales_data.resample('M').sum()

                # Check data length and select forecasting method
                if monthly_sales.shape[0] < 3:
                    messages.error(request, "Not enough data for prediction. Please provide at least 3 months of data.")
                    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/upload/'))
                elif 3 <= monthly_sales.shape[0] <= 5:
                    # Use Linear Regression for 3-5 months of data
                    sales = monthly_sales['total_sales'].values
                    dates = np.arange(len(sales)).reshape(-1, 1)
                    future_dates = np.arange(len(sales), len(sales) + 6).reshape(-1, 1)

                    # Linear Regression model
                    model = LinearRegression()
                    model.fit(dates, sales)
                    predictions = model.predict(future_dates)
                    predictions = [max(round(value, 2), 0) for value in predictions]  # Avoid negatives

                    forecast_dates = pd.date_range(start=monthly_sales.index[-1], periods=7, freq='M')[1:]
                    forecast_df = pd.DataFrame({'date': forecast_dates, 'predicted_sales': predictions})
                else:
                    # Use ARIMA for 6+ months of data
                    model = ARIMA(monthly_sales['total_sales'], order=(5, 1, 0))
                    model_fit = model.fit()
                    forecast = model_fit.forecast(steps=6)
                    forecast = [max(round(value, 2), 0) for value in forecast]  # Avoid negatives

                    forecast_dates = pd.date_range(start=monthly_sales.index[-1], periods=7, freq='M')[1:]
                    forecast_df = pd.DataFrame({'date': forecast_dates, 'predicted_sales': forecast})

                # Prepare actual sales data
                last_6_months_sales = monthly_sales.tail(6)
                last_6_months_sales_df = last_6_months_sales.reset_index()[['date', 'total_sales']]
                last_6_months_sales_df.columns = ['date', 'value']

                # Prepare predicted sales data
                forecast_df.columns = ['date', 'value']

                # Format dates and combine data
                last_6_months_sales_df['date'] = last_6_months_sales_df['date'].dt.strftime('%B %d, %Y')
                forecast_df['date'] = forecast_df['date'].dt.strftime('%B %d, %Y')

                last_6_months_sales_df['type'] = 'Actual Sales'
                forecast_df['type'] = 'Predicted Sales'

                combined_sales = pd.concat([last_6_months_sales_df, forecast_df], ignore_index=True)
                chart_data = combined_sales.to_dict(orient='list')

                actual_sales_table = last_6_months_sales_df.to_dict(orient='records')
                predicted_sales_table = forecast_df.to_dict(orient='records')

                messages.success(request, "File processed successfully. The chart and data are ready.")
                return render(request, 'predict_sales.html', {
                    'uploaded_file_name': uploaded_file_name,
                    'actual_sales_table': actual_sales_table,
                    'predicted_sales_table': predicted_sales_table,
                    'chart_data': json.dumps(chart_data)
                })

            except Exception as e:
                messages.error(request, f"Error processing the file: {str(e)}")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/upload/'))

    else:
        form = SalesDataUploadForm()

    return render(request, 'upload.html', {'form': form})










 

