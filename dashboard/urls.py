from django.urls import path
from . import views


urlpatterns = [
    path('', views.landing_view, name='landing'), 
    path('upload', views.upload, name='upload_and_visualize'), 
    path('visualize/<int:dataset_id>/', views.visualize, name='visualize_dataset'),  
    path('clear_dataset/<int:dataset_id>/', views.clear_dataset, name='clear_dataset'), 
    path('download/<int:dataset_id>/', views.download_dataset, name='download_dataset'), 
    path('sales-comparison/<int:dataset_id>/', views.compare_sales, name='sales_comparison'),
    path('compare-existing-sales/<int:dataset_id>/', views.compare_existing_sales, name='compare_existing_sales'),
    path('dataset-visualization/<int:dataset_id>/', views.visualize_comparison, name='dataset_visualization'),
    path('predicted-sale/', views.upload_and_predict, name='upload_and_predict'),
    # path('portfolio/', views.portfolio_home, name='portfolio_home'), 
    path('get_dataset_rows/<int:dataset_id>/', views.get_dataset_rows, name='get_dataset_rows'),



    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('password-reset-success/', views.password_reset_success, name='password_reset_success'),
    path('profile/', views.profile_view, name='profile'),
]


