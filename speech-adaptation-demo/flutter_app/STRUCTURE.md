# Unified Flutter App Structure

This document describes the unified Flutter app that combines all three applications (Demo, Research, Study) into one beautiful, easy-to-understand interface.

## Architecture

```
MainScreen (PageView + Drawer + Bottom Nav)
├── Home Screen
├── Demo Flow Screen → Demo Results Screen
├── Research Home Screen
├── Study Home Screen
├── Profiles Screen
└── Analytics Screen
```

## Navigation

- **Drawer**: Side menu with all sections + About
- **Bottom Navigation Bar**: Quick access to 6 main sections
- **PageView**: Swipe between sections (smooth transitions)

## Screen Descriptions

### 1. Home Screen (`screens/home_screen.dart`)
- **Hero Section**: Gradient header with app name and description
- **Quick Actions**: Cards for Demo, Research, Study
- **Data Summary**: Shows pre-loaded data (speakers, profiles, audio files) if patent build was run
- **How It Works**: Three step cards explaining Baseline → Personalized → Repaired

### 2. Demo Flow (`screens/demo/`)
- **Demo Flow Screen**: Simple 3-step form:
  1. Select Profile (dropdown)
  2. Select Audio (dropdown from demo list)
  3. Optional Ground Truth
- **Demo Results Screen**: Three result cards showing Baseline, Personalized, Repaired transcripts + WER if available

### 3. Research Home (`screens/research/research_home_screen.dart`)
- Feature cards for:
  - Run Pipeline (full metrics)
  - Continual Learning
  - Pronunciation Patterns
  - Model Comparison
  - Advanced Analytics
  - Thesis Export
- Each card links to future detailed screens

### 4. Study Home (`screens/study/study_home_screen.dart`)
- Overview of 5 study tasks
- Task list with numbers
- Start Study button

### 5. Profiles (`screens/profiles/profiles_screen.dart`)
- List of all profiles
- Profile cards with avatar, name, ID
- Floating action button to create new profile

### 6. Analytics (`screens/analytics/analytics_screen.dart`)
- Metric cards (WER, SemScore, Task Success)
- Export options (Thesis Export)

## Design Principles

- **Material 3**: Modern design system with teal primary color
- **Minimal**: Clean, uncluttered interface
- **Sequential**: Clear step-by-step flows
- **Beautiful**: Cards, gradients, icons, proper spacing
- **Consistent**: Same card style, spacing, typography throughout

## File Structure

```
lib/
├── main.dart                    # Main app + MainScreen with navigation
├── api/
│   └── client.dart              # API client for backend calls
└── screens/
    ├── home_screen.dart         # Home dashboard
    ├── demo/
    │   ├── demo_flow_screen.dart
    │   └── demo_results_screen.dart
    ├── research/
    │   └── research_home_screen.dart
    ├── study/
    │   └── study_home_screen.dart
    ├── profiles/
    │   └── profiles_screen.dart
    └── analytics/
        └── analytics_screen.dart
```

## Running the App

1. **Start backend**: `python api_server.py` (from `speech-adaptation-demo`)
2. **Run Flutter**: `flutter run` (from `flutter_app`)
3. **Navigate**: Use drawer or bottom nav bar

## Next Steps

- Implement full Research features (Continual Learning, Model Comparison, etc.)
- Implement Study flow (5 tasks with recording)
- Add profile creation/editing
- Add analytics charts (WER over time, etc.)
- Connect all screens to backend API
