import 'package:flutter/material.dart';
import '../api/client.dart';

class RunScreen extends StatefulWidget {
  const RunScreen({super.key});

  @override
  State<RunScreen> createState() => _RunScreenState();
}

class _RunScreenState extends State<RunScreen> {
  final _api = SpeechAdaptationApi();
  List<Map<String, dynamic>> _profiles = [];
  List<Map<String, dynamic>> _demoAudio = [];
  String? _selectedProfileId;
  String? _selectedDemoPath;
  String _groundTruth = '';
  String _contextHints = '';
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _error = null; });
    try {
      final profiles = await _api.getProfiles();
      final demo = await _api.getDemoAudio();
      if (mounted) {
        setState(() {
          _profiles = profiles;
          _demoAudio = demo;
          if (_profiles.isNotEmpty && _selectedProfileId == null) {
            _selectedProfileId = _profiles.first['id'] as String?;
          }
          if (_demoAudio.isNotEmpty && _selectedDemoPath == null) {
            _selectedDemoPath = _demoAudio.first['path'] as String?;
          }
        });
      }
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); });
    }
  }

  Future<void> _runPipeline() async {
    if (_selectedProfileId == null || _selectedDemoPath == null) {
      setState(() => _error = 'Select a profile and an audio file.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final result = await _api.runPipelineWithDemoPath(
        profileId: _selectedProfileId!,
        demoAudioPath: _selectedDemoPath!,
        groundTruth: _groundTruth,
        contextHints: _contextHints,
      );
      if (mounted) {
        Navigator.pushNamed(context, '/results', arguments: result);
      }
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); });
    } finally {
      if (mounted) setState(() { _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Run pipeline'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('1. Select profile', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _selectedProfileId,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              items: _profiles.map((p) {
                final id = p['id'] as String? ?? '';
                final name = p['name'] as String? ?? id;
                return DropdownMenuItem(value: id, child: Text(name));
              }).toList(),
              onChanged: (v) => setState(() => _selectedProfileId = v),
            ),
            const SizedBox(height: 24),
            const Text('2. Select audio', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _selectedDemoPath,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              items: _demoAudio.map((a) {
                final path = a['path'] as String? ?? '';
                final label = a['label'] as String? ?? path;
                return DropdownMenuItem(value: path, child: Text(label, overflow: TextOverflow.ellipsis));
              }).toList(),
              onChanged: (v) => setState(() => _selectedDemoPath = v),
            ),
            const SizedBox(height: 24),
            const Text('3. Optional: ground truth (what was said)', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            TextField(
              decoration: const InputDecoration(border: OutlineInputBorder(), hintText: 'e.g. hello'),
              onChanged: (v) => _groundTruth = v,
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: const InputDecoration(border: OutlineInputBorder(), hintText: 'Context hints (optional)'),
              onChanged: (v) => _contextHints = v,
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Card(color: Colors.red.shade50, child: Padding(padding: const EdgeInsets.all(12.0), child: Text(_error!, style: TextStyle(color: Colors.red.shade900))))],
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _loading ? null : _runPipeline,
              style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
              child: _loading ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Run pipeline'),
            ),
          ],
        ),
      ),
    );
  }
}
