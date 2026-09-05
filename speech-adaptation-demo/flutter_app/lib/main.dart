import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/demo/demo_flow_screen.dart';
import 'screens/research/research_home_screen.dart';
import 'screens/study/study_home_screen.dart';
import 'screens/profiles/profiles_screen.dart';
import 'screens/analytics/analytics_screen.dart';

void main() {
  runApp(const SpeechAdaptationApp());
}

class SpeechAdaptationApp extends StatelessWidget {
  const SpeechAdaptationApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Speech Adaptation',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF00695C),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        cardTheme: CardTheme(
          elevation: 1,
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
        ),
      ),
      home: const MainScreen(),
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;
  final PageController _pageController = PageController();

  final List<Widget> _screens = [
    const HomeScreen(),
    const DemoFlowScreen(),
    const ResearchHomeScreen(),
    const StudyHomeScreen(),
    const ProfilesScreen(),
    const AnalyticsScreen(),
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
    _pageController.jumpToPage(index);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      drawer: _buildDrawer(context),
      appBar: AppBar(
        title: const Text('Speech Adaptation'),
        elevation: 0,
      ),
      body: PageView(
        controller: _pageController,
        onPageChanged: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 8,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _navItem(context, 0, Icons.home_rounded, 'Home'),
                _navItem(context, 1, Icons.play_circle_outline_rounded, 'Demo'),
                _navItem(context, 2, Icons.science_outlined, 'Research'),
                _navItem(context, 3, Icons.assignment_outlined, 'Study'),
                _navItem(context, 4, Icons.person_outline_rounded, 'Profiles'),
                _navItem(context, 5, Icons.analytics_outlined, 'Analytics'),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDrawer(BuildContext context) {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Theme.of(context).colorScheme.primary,
                  Theme.of(context).colorScheme.primaryContainer,
                ],
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Icon(
                  Icons.mic,
                  size: 48,
                  color: Theme.of(context).colorScheme.onPrimary,
                ),
                const SizedBox(height: 8),
                Text(
                  'Speech Adaptation',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: Theme.of(context).colorScheme.onPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                ),
                Text(
                  'Three-Layer Pipeline',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Theme.of(context).colorScheme.onPrimary.withOpacity(0.9),
                      ),
                ),
              ],
            ),
          ),
          _buildDrawerItem(
            context,
            icon: Icons.home,
            title: 'Home',
            index: 0,
          ),
          _buildDrawerItem(
            context,
            icon: Icons.play_circle_outline,
            title: 'Demo',
            subtitle: 'Quick pipeline test',
            index: 1,
          ),
          _buildDrawerItem(
            context,
            icon: Icons.science_outlined,
            title: 'Research',
            subtitle: 'Full features & analysis',
            index: 2,
          ),
          _buildDrawerItem(
            context,
            icon: Icons.assignment_outlined,
            title: 'Study',
            subtitle: '5-task validation',
            index: 3,
          ),
          const Divider(),
          _buildDrawerItem(
            context,
            icon: Icons.person_outline,
            title: 'Profiles',
            index: 4,
          ),
          _buildDrawerItem(
            context,
            icon: Icons.analytics_outlined,
            title: 'Analytics',
            index: 5,
          ),
          const Divider(),
          _buildDrawerItem(
            context,
            icon: Icons.info_outline,
            title: 'About',
            index: -1,
            onTap: () {
              Navigator.pop(context);
              showAboutDialog(
                context: context,
                applicationName: 'Speech Adaptation',
                applicationVersion: '1.0.0',
                applicationIcon: const Icon(Icons.mic, size: 48),
                children: [
                  const Text(
                    'Three-layer speech recognition:\n'
                    '1. Baseline ASR\n'
                    '2. Personalized ASR\n'
                    '3. Semantic Repair',
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildDrawerItem(
    BuildContext context, {
    required IconData icon,
    required String title,
    String? subtitle,
    required int index,
    VoidCallback? onTap,
  }) {
    return ListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: subtitle != null ? Text(subtitle) : null,
      selected: index >= 0 && _selectedIndex == index,
      onTap: onTap ?? () => _navigateToScreen(context, index),
    );
  }

  void _navigateToScreen(BuildContext context, int index) {
    if (index < 0) return;
    Navigator.pop(context);
    setState(() {
      _selectedIndex = index;
    });
    _pageController.jumpToPage(index);
  }

  Widget _navItem(BuildContext context, int index, IconData icon, String label) {
    final selected = _selectedIndex == index;
    return Tooltip(
      message: label,
      child: InkWell(
        onTap: () => _onItemTapped(index),
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 22,
                color: selected
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.onSurfaceVariant.withOpacity(0.7),
              ),
              if (selected) ...[
                const SizedBox(height: 4),
                Text(
                  label,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
