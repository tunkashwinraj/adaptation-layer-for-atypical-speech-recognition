import 'package:flutter/material.dart';
import '../../widgets/info_tooltip.dart';

class DemoResultsScreen extends StatelessWidget {
  final Map<String, dynamic> result;

  const DemoResultsScreen({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final baseline = result['baseline_transcript'] as String? ?? '';
    final personalized = result['personalized_transcript'] as String? ?? '';
    final repaired = result['repaired_transcript'] as String? ?? '';
    final accuracy = result['accuracy'] as List? ?? [];

    String werLine = '';
    if (accuracy.isNotEmpty) {
      final parts = accuracy.map((e) {
        final stage = e['Stage'] ?? '';
        final wer = e['WER'] ?? 0.0;
        return '$stage: ${(wer * 100).toStringAsFixed(1)}%';
      }).toList();
      werLine = parts.join('  →  ');
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Results')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (werLine.isNotEmpty)
              Card(
                color: Theme.of(context).colorScheme.primaryContainer,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Flexible(
                        child: Text(
                          'WER: $werLine',
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                      const SizedBox(width: 4),
                      InfoTooltip(
                        message: 'Word Error Rate (WER): percentage of words wrong vs ground truth. Lower is better. Shows how each stage (Baseline, Personalized, Repaired) compares.',
                      ),
                    ],
                  ),
                ),
              ),
            if (werLine.isNotEmpty) const SizedBox(height: 12),
            _buildResultCard(
              context,
              step: 1,
              title: 'Baseline ASR',
              subtitle: 'Generic speech-to-text',
              info: 'Output from the generic ASR engine without any user-specific vocabulary or corrections.',
              text: baseline,
              color: Colors.blue,
            ),
            _buildResultCard(
              context,
              step: 2,
              title: 'Personalized ASR',
              subtitle: 'With your vocabulary',
              info: 'Same engine but boosted with this profile\'s custom vocabulary and learned pronunciation patterns.',
              text: personalized,
              color: Colors.purple,
            ),
            _buildResultCard(
              context,
              step: 3,
              title: 'Semantic Repair',
              subtitle: 'Final cleaned output',
              info: 'AI post-processing fixes grammar, clarity, and wording of the personalized transcript.',
              text: repaired,
              color: Colors.teal,
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.arrow_back, size: 18),
              label: const Text('Run Another'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultCard(
    BuildContext context, {
    required int step,
    required String title,
    required String subtitle,
    required String info,
    required String text,
    required Color color,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Center(
                    child: Text(
                      '$step',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                        color: color,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                      Text(
                        subtitle,
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                InfoTooltip(message: info),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.grey[50],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                text.isEmpty ? '—' : text,
                style: const TextStyle(fontSize: 14),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
