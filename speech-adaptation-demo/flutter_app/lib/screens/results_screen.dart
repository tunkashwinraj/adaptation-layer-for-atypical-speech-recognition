import 'package:flutter/material.dart';

class ResultsScreen extends StatelessWidget {
  final Map<String, dynamic> result;

  const ResultsScreen({super.key, required this.result});

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
      appBar: AppBar(
        title: const Text('Results'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.popUntil(context, (r) => r.isFirst),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (werLine.isNotEmpty)
              Card(
                color: Colors.teal.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Text('Word error rate: $werLine', style: const TextStyle(fontWeight: FontWeight.w500)),
                ),
              ),
            const SizedBox(height: 16),
            _ResultCard(title: '1. Baseline (generic ASR)', text: baseline),
            _ResultCard(title: '2. Personalized (your vocabulary)', text: personalized),
            _ResultCard(title: '3. Repaired (final)', text: repaired),
            const SizedBox(height: 24),
            OutlinedButton(
              onPressed: () => Navigator.popUntil(context, (r) => r.isFirst),
              child: const Text('Back to home'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  final String title;
  final String text;

  const _ResultCard({required this.title, required this.text});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(text.isEmpty ? '—' : text),
          ],
        ),
      ),
    );
  }
}
