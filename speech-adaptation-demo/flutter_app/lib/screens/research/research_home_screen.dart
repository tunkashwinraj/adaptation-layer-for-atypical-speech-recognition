import 'package:flutter/material.dart';

class ResearchHomeScreen extends StatelessWidget {
  const ResearchHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildHeader(context),
            const SizedBox(height: 16),
            _buildFeatureCard(
              context,
              icon: Icons.play_circle,
              title: 'Run Pipeline',
              description: 'Full pipeline with all metrics and analysis',
              color: Colors.blue,
            ),
            _buildFeatureCard(
              context,
              icon: Icons.school,
              title: 'Continual Learning',
              description: 'Submit corrections and learn patterns',
              color: Colors.green,
            ),
            _buildFeatureCard(
              context,
              icon: Icons.record_voice_over,
              title: 'Pronunciation Patterns',
              description: 'View detected pronunciation variations',
              color: Colors.orange,
            ),
            _buildFeatureCard(
              context,
              icon: Icons.compare_arrows,
              title: 'Model Comparison',
              description: 'Compare different ASR models',
              color: Colors.purple,
            ),
            _buildFeatureCard(
              context,
              icon: Icons.analytics,
              title: 'Advanced Analytics',
              description: 'Detailed metrics and performance tracking',
              color: Colors.teal,
            ),
            _buildFeatureCard(
              context,
              icon: Icons.picture_as_pdf,
              title: 'Thesis Export',
              description: 'Generate LaTeX tables and figures',
              color: Colors.red,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Research Mode',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 4),
        Text(
          'Full-featured pipeline with advanced analysis',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey[600],
              ),
        ),
      ],
    );
  }

  Widget _buildFeatureCard(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String description,
    required Color color,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 6),
      child: ListTile(
        dense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
        subtitle: Text(description, style: const TextStyle(fontSize: 12)),
        trailing: const Icon(Icons.chevron_right, size: 20),
        onTap: () {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$title - Coming soon')),
          );
        },
      ),
    );
  }
}
