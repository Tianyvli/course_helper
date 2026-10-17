import 'package:flutter_bmflocation/flutter_bmflocation.dart';

/// iOS returns coordinates without Android's locType field.
bool hasLocationCoordinates(BaiduLocation result, {required bool isIOS}) {
  if (result.latitude == null || result.longitude == null) return false;
  if (isIOS) return result.errorCode == null || result.errorCode == 0;
  return result.locType != null && result.locType! > 0;
}
