from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, QuizForm
from .models import RoommateProfile

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('quiz')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            try:
                if user.roommateprofile:
                    return redirect('dashboard')
            except RoommateProfile.DoesNotExist:
                return redirect('quiz')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def quiz_view(request):
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

@login_required
def dashboard_view(request):
    try:
        my_profile = request.user.roommateprofile
    except RoommateProfile.DoesNotExist:
        return redirect('quiz')

    all_profiles = RoommateProfile.objects.exclude(user=request.user)
    matches = []

    for other in all_profiles:
        score = 100
        
        # 1. Sleep Schedule Impact (High Weight: 25 pts)
        if my_profile.sleep_schedule != other.sleep_schedule:
            score -= 25
            
        # 2. Study Habit Impact (Medium Weight: 15 pts)
        if my_profile.study_habit != other.study_habit:
            score -= 15

        # 3. Cleanliness Diff (Weight: 5 pts per level diff)
        clean_diff = abs(my_profile.cleanliness_level - other.cleanliness_level)
        score -= (clean_diff * 5)

        # 4. Noise Tolerance Diff (Weight: 5 pts per level diff)
        noise_diff = abs(my_profile.noise_tolerance - other.noise_tolerance)
        score -= (noise_diff * 5)

        # Cap score at 0 minimum
        final_score = max(score, 0)

        matches.append({
            'name': other.user.first_name or other.user.username,
            'score': final_score,
            'room': other.hostel_room_no,
            'sleep': other.sleep_schedule,
            'clean': other.cleanliness_level,
            'profile': other
        })

    # Sort by score descending (Highest first)
    matches.sort(key=lambda x: x['score'], reverse=True)
    top_matches = matches[:5]

    return render(request, 'dashboard.html', {'matches': top_matches})

def logout_view(request):
    logout(request)
    return redirect('login')