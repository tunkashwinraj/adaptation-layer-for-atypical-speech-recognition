import 'package:flutter/material.dart';
import '../../api/client.dart';
import '../../widgets/info_tooltip.dart';
import 'demo_results_screen.dart';

class DemoFlowScreen extends StatefulWidget {
  const DemoFlowScreen({super.key});

  @override
  State<DemoFlowScreen> createState() => _DemoFlowScreenState();
}

class _DemoFlowScreenState extends State<DemoFlowScreen> {
  final _api = SpeechAdaptationApi();
  List<Map<String, dynamic>> _profiles = [];
  List<Map<String, dynamic>> _demoAudio = [];
  String? _selectedProfileId;
  String? _selectedDemoPath;
  String _groundTruth = '';
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
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
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _runPipeline() async {
    if (_selectedProfileId == null || _selectedDemoPath == null) {
      setState(() => _error = 'Select a profile and an audio file.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await _api.runPipelineWithDemoPath(
        profileId: _selectedProfileId!,
        demoAudioPath: _selectedDemoPath!,
        groundTruth: _groundTruth,
      );
      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => DemoResultsScreen(result: result),
          ),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

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
            _buildStep(context, 1, 'Select Profile', 'User profile whose vocabulary is used for personalized ASR.', _buildProfileSelector()),
            const SizedBox(height: 12),
            _buildStep(context, 2, 'Select Audio', 'Audio file to transcribe. Use a file from the list or upload your own.', _buildAudioSelector()),
            const SizedBox(height: 12),
            _buildStep(context, 3, 'Ground Truth (optional)', 'What was actually said. If provided, we compute Word Error Rate (WER) to show accuracy.', _buildGroundTruthField()),
            if (_error != null) ...[
              const SizedBox(height: 10),
              _buildErrorCard(),
            ],
            const SizedBox(height: 16),
            _buildRunButton(),
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
          'Demo Pipeline',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 4),
        Text(
          'Quick test of the three-layer pipeline',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey[600],
              ),
        ),
      ],
    );
  }

  Widget _buildStep(BuildContext context, int step, String title, String infoMessage, Widget content) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Center(
                    child: Text(
                      '$step',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(width: 4),
                InfoTooltip(message: infoMessage),
              ],
            ),
            const SizedBox(height: 10),
            content,
          ],
        ),
      ),
    );
  }

  Widget _buildProfileSelector() {
    return DropdownButtonFormField<String>(
      value: _selectedProfileId,
      decoration: const InputDecoration(
        isDense: true,
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        labelText: 'Profile',
      ),
      items: _profiles.map((p) {
        final id = p['id'] as String? ?? '';
        final name = p['name'] as String? ?? id;
        return DropdownMenuItem(value: id, child: Text(name));
      }).toList(),
      onChanged: (v) => setState(() => _selectedProfileId = v),
    );
  }

  Widget _buildAudioSelector() {
    return DropdownButtonFormField<String>(
      value: _selectedDemoPath,
      decoration: const InputDecoration(
        isDense: true,
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        labelText: 'Demo Audio',
      ),
      items: _demoAudio.map((a) {
        final path = a['path'] as String? ?? '';
        final label = a['label'] as String? ?? path;
        return DropdownMenuItem(
          value: path,
          child: Text(label, overflow: TextOverflow.ellipsis),
        );
      }).toList(),
      onChanged: (v) => setState(() => _selectedDemoPath = v),
    );
  }

  Widget _buildGroundTruthField() {
    return TextField(
      decoration: const InputDecoration(
        isDense: true,
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        labelText: 'What was actually said (optional)',
        hintText: 'e.g. hello',
      ),
      onChanged: (v) => _groundTruth = v,
    );
  }

  Widget _buildErrorCard() {
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Row(
          children: [
            Icon(Icons.error_outline, size: 20, color: Colors.red.shade900),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                _error!,
                style: TextStyle(fontSize: 13, color: Colors.red.shade900),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRunButton() {
    return ElevatedButton.icon(
      onPressed: _loading ? null : _runPipeline,
      icon: _loading
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.play_arrow, size: 20),
      label: Text(_loading ? 'Running...' : 'Run Pipeline'),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 12),
      ),
    );
  }
}
