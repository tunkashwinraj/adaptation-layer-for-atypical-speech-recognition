import 'package:flutter/material.dart';

/// Small (i) icon that shows [message] on hover (desktop/web) or tap (mobile).
/// Use next to section titles or fields to explain what they mean.
class InfoTooltip extends StatelessWidget {
  final String message;

  const InfoTooltip({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: message,
      waitDuration: const Duration(milliseconds: 300),
      preferBelow: false,
      child: InkWell(
        onTap: () => _showInfo(context),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Icon(
            Icons.info_outline,
            size: 18,
            color: Theme.of(context).colorScheme.onSurfaceVariant.withOpacity(0.7),
          ),
        ),
      ),
    );
  }

  void _showInfo(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(message),
        contentTextStyle: Theme.of(context).textTheme.bodyMedium,
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}

/// Wraps a label with an optional info icon. Use for section headers.
class LabelWithInfo extends StatelessWidget {
  final String label;
  final String? infoMessage;

  const LabelWithInfo({super.key, required this.label, this.infoMessage});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label),
        if (infoMessage != null) ...[
          const SizedBox(width: 4),
          InfoTooltip(message: infoMessage!),
        ],
      ],
    );
  }
}
