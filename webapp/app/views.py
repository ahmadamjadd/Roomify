import os
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from .models import RoommateProfile, User, MatchInteraction
from .forms import UserRegisterForm, QuizForm, EmailAuthenticationForm, UpdateForm
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Max, Avg
  
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from django.db.models import Max, Avg
  

def email_user(request, user):
    """Sends a verification email to the user."""
    try:
        current_site = get_current_site(request)
        mail_subject = 'Activate your Roommate Finder account.'
        message = render_to_string('acc_active_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
        })
        to_email = user.email
        send_mail(
            mail_subject,
            message,
            os.getenv('EMAIL_ADDRESS'),
            [to_email]
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, 'Thank you for your email confirmation. You are now logged in!')
        return redirect('quiz')
    else:
        messages.error(request, 'Activation link is invalid or expired!')
        return redirect('register')

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.set_password(form.cleaned_data['password'])
            user.save()
            if email_user(request, user):
                messages.info(request, 'Please confirm your email address to complete the registration.')
                return redirect('login')
            else:
                user.delete()
                messages.error(request, 'Registration failed due to an email error. Please try again.')
                return redirect('register')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(data=request.POST)
        if form.is_valid():
            user  = form.get_user()
            login(request, user)
            try:
                if hasattr(user, 'roommateprofile'):
                    return redirect('dashboard')
                else:
                    return redirect('quiz')
            except RoommateProfile.DoesNotExist:
                return redirect('quiz')
    else:
        form = EmailAuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def quiz_view(request):
    if hasattr(request.user, 'roommateprofile'):
        return redirect('dashboard')

    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('dashboard')
    else:
        form = QuizForm()
    return render(request, 'quiz.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def add_phone_number(request):
    """Separate view to handle existing users adding a phone number"""
    if request.method == 'POST':
        form = UpdateForm(request.POST, instance=request.user.roommateprofile)
        if form.is_valid():
            form.save()
            messages.success(request, "Phone number updated! You are now visible to matches.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please enter a valid phone number starting with 03.")
    return redirect('dashboard')
 

@login_required
def track_whatsapp_click(request, target_id):
    """
    Intermediary view to log the click (Metric 1) before redirecting to WhatsApp.
    """
    try:
        target_user = User.objects.get(pk=target_id)
  
        interaction = MatchInteraction.objects.filter(
            viewer=request.user,
            target=target_user
        ).first()

        if interaction:
            interaction.whatsapp_clicked = True
            interaction.save()

  
        phone_number = target_user.roommateprofile.phone_number
        if phone_number:
            wa_url = f"https://wa.me/{phone_number}?text=Hey!%20I%20saw%20we%20matched%20on%20Roomify."
            return redirect(wa_url)

    except User.DoesNotExist:
        pass

    return redirect('dashboard')

@staff_member_required
def metrics_dashboard(request):
    """
    Calculates the 3 requested metrics for the admin.
    """
    if not request.user.is_staff:
        return redirect('dashboard')

    total_views = MatchInteraction.objects.count()
    total_clicks = MatchInteraction.objects.filter(whatsapp_clicked=True).count()
    mcr = (total_clicks / total_views * 100) if total_views > 0 else 0

    total_users = User.objects.count()
    total_profiles = RoommateProfile.objects.count()
    pcr = (total_profiles / total_users * 100) if total_users > 0 else 0

    avg_top_score_data = MatchInteraction.objects.values('viewer').annotate(max_score=Max('match_score')).aggregate(Avg('max_score'))
    avg_top_score = avg_top_score_data['max_score__avg'] or 0

    context = {
            'mcr': mcr,
            'pcr': pcr,
            'avg_top_score': avg_top_score,
            'total_clicks': total_clicks,
            'total_views': total_views,
            'total_users': total_users,
            'total_profiles': total_profiles,
        }

    return render(request, 'metrics.html', context)


  
def get_knn_score(my_profile, all_profiles, k=5):
    """
    Calculates a k-NN similarity score for each profile relative to the user.
    The score is based on the inverse of the distance (similarity).
    """
    if not all_profiles:
        return {}
  
    sleep_map = {'Early': 0, 'Late': 1}
    study_map = {'Morning': 0, 'Night': 1, 'Mix': 0.5}

    def extract_features(profile):
        return [
            sleep_map.get(profile.sleep_schedule, 0.5), # Scale is 0 to 1
            profile.cleanliness_level,                   # Scale is 1 to 5
            profile.noise_tolerance,                     # Scale is 1 to 5
            study_map.get(profile.study_habit, 0.5),     # Scale is 0 to 1
        ]

  
    profile_data = [extract_features(p) for p in list(all_profiles) + [my_profile]]
    profile_users = [p.user.id for p in all_profiles] + [my_profile.user.id]

    my_profile_index = len(profile_users) - 1

  
    df = pd.DataFrame(profile_data, columns=['sleep', 'cleanliness', 'noise', 'study'])
    
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df.values)
    
    X_train = scaled_features[:-1] # All others
    X_test = scaled_features[my_profile_index].reshape(1, -1) # Current user

    if X_train.shape[0] < k:
        k = X_train.shape[0] # Adjust K if not enough neighbors

    if k == 0:
        return {}

    knn = NearestNeighbors(n_neighbors=k, algorithm='brute', metric='euclidean')
    knn.fit(X_train)
    distances, indices = knn.kneighbors(X_test, n_neighbors=X_train.shape[0], return_distance=True)
    distances = distances.flatten()
    indices = indices.flatten()
    max_distance = np.max(distances) if distances.size > 0 else 1 
    
    knn_scores = {}
    for dist, idx in zip(distances, indices):
  
        normalized_distance = dist / (max_distance + 1e-6)
        similarity = (1 - normalized_distance) * 100 # 0 (low sim) to 100 (high sim)
        
  
        target_user_id = profile_users[idx]
        knn_scores[target_user_id] = round(similarity)

    return knn_scores

@login_required
def dashboard_view(request):
    try:
        my_profile = request.user.roommateprofile
    except RoommateProfile.DoesNotExist:
        return redirect('quiz')

    missing_phone = False
    phone_form = None

    if not my_profile.phone_number:
        missing_phone = True
        phone_form = UpdateForm(instance=my_profile)

    all_profiles = RoommateProfile.objects.exclude(user=request.user)
    
    knn_scores = get_knn_score(my_profile, all_profiles, k=5) 
    
    matches = []
    
  
    print(f"\n--- MATCHING PROCESS FOR USER: {request.user.username} ---")
    
    for other in all_profiles:
  
        heuristic_score = 100
        if my_profile.sleep_schedule != other.sleep_schedule: heuristic_score -= 25
        if my_profile.study_habit != other.study_habit: heuristic_score -= 15
        heuristic_score -= (abs(my_profile.cleanliness_level - other.cleanliness_level) * 5)
        heuristic_score -= (abs(my_profile.noise_tolerance - other.noise_tolerance) * 5)
        final_heuristic_score = max(heuristic_score, 0)
  
 
        ml_score = knn_scores.get(other.user.id, 0) 
  
        combined_score = round((0.6 * final_heuristic_score) + (0.4 * ml_score))
  
        print(f"Target: {other.user.username:<10} | Heuristic: {final_heuristic_score:>3}% | KNN: {ml_score:>3}% | Combined (60/40): {combined_score:>3}%")
        
        matches.append({
            'name': other.user.first_name or other.user.username,
            'score': combined_score,        
            'sleep': other.sleep_schedule,
            'clean': other.cleanliness_level,
            'phone': other.phone_number,
            'profile': other,
            'user_id': other.user.id
        })

    print("---------------------------------------------------\n")
  

    matches.sort(key=lambda x: x['score'], reverse=True)
    top_matches = matches[:5]

  
  
    for match in top_matches:
  
        MatchInteraction.objects.update_or_create(
            viewer=request.user,
            target=match['profile'].user,
            defaults={'match_score': match['score']}
        )
  

    context = {
        'matches': top_matches,
        'missing_phone': missing_phone,
        'phone_form': phone_form
    }

    return render(request, 'dashboard.html', context)