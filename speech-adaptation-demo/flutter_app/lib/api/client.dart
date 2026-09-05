import 'dart:convert';
import 'package:http/http.dart' as http;

/// Base URL for the Speech Adaptation API. Change for your environment.
/// Android emulator: use 10.0.2.2:8000 instead of localhost.
const String kBaseUrl = 'http://localhost:8000';

class SpeechAdaptationApi {
  final String baseUrl;

  SpeechAdaptationApi({this.baseUrl = kBaseUrl});

  Future<Map<String, dynamic>> health() async {
    final r = await http.get(Uri.parse('$baseUrl/api/health'));
    if (r.statusCode != 200) throw Exception('Health check failed');
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getProfiles() async {
    final r = await http.get(Uri.parse('$baseUrl/api/profiles'));
    if (r.statusCode != 200) throw Exception(r.body);
    final list = jsonDecode(r.body) as List;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<Map<String, dynamic>> getProfileVocabulary(String userId) async {
    final r = await http.get(Uri.parse('$baseUrl/api/profiles/$userId/vocabulary'));
    if (r.statusCode != 200) throw Exception(r.body);
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getDemoAudio() async {
    final r = await http.get(Uri.parse('$baseUrl/api/demo-audio'));
    if (r.statusCode != 200) throw Exception(r.body);
    final list = jsonDecode(r.body) as List;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<Map<String, dynamic>> getPatentSummary() async {
    final r = await http.get(Uri.parse('$baseUrl/api/patent-summary'));
    if (r.statusCode != 200) return {'present': false};
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  /// Run pipeline with a demo audio path (from getDemoAudio()).
  Future<Map<String, dynamic>> runPipelineWithDemoPath({
    required String profileId,
    required String demoAudioPath,
    String groundTruth = '',
    String contextHints = '',
  }) async {
    final uri = Uri.parse('$baseUrl/api/pipeline/run');
    final request = http.MultipartRequest('POST', uri);
    request.fields['profile_id'] = profileId;
    request.fields['demo_audio_path'] = demoAudioPath;
    request.fields['ground_truth'] = groundTruth;
    request.fields['context_hints'] = contextHints;
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode != 200) {
      try {
        final err = jsonDecode(response.body) as Map<String, dynamic>;
        throw Exception(err['detail'] ?? response.body);
      } catch (e) {
        if (e is Exception) rethrow;
        throw Exception(response.body);
      }
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// Run pipeline with an uploaded audio file (bytes).
  Future<Map<String, dynamic>> runPipelineWithFile({
    required String profileId,
    required List<int> audioBytes,
    required String filename,
    String groundTruth = '',
    String contextHints = '',
  }) async {
    final uri = Uri.parse('$baseUrl/api/pipeline/run');
    final request = http.MultipartRequest('POST', uri);
    request.fields['profile_id'] = profileId;
    request.fields['ground_truth'] = groundTruth;
    request.fields['context_hints'] = contextHints;
    request.files.add(http.MultipartFile.fromBytes(
      'audio',
      audioBytes,
      filename: filename,
    ));
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode != 200) {
      try {
        final err = jsonDecode(response.body) as Map<String, dynamic>;
        throw Exception(err['detail'] ?? response.body);
      } catch (e) {
        if (e is Exception) rethrow;
        throw Exception(response.body);
      }
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
