import 'package:course_helper/utils/location_result.dart';
import 'package:flutter_bmflocation/flutter_bmflocation.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('iOS accepts coordinates without Android locType', () {
    final location = BaiduLocation(latitude: 23.1, longitude: 113.3);
    expect(hasLocationCoordinates(location, isIOS: true), isTrue);
    expect(hasLocationCoordinates(location, isIOS: false), isFalse);
  });

  test('iOS rejects location errors and missing coordinates', () {
    expect(hasLocationCoordinates(
      BaiduLocation(latitude: 23.1, longitude: 113.3, errorCode: 1),
      isIOS: true,
    ), isFalse);
    expect(hasLocationCoordinates(BaiduLocation(), isIOS: true), isFalse);
  });

  test('Android keeps its locType requirement', () {
    expect(hasLocationCoordinates(
      BaiduLocation(latitude: 23.1, longitude: 113.3, locType: 161),
      isIOS: false,
    ), isTrue);
    expect(hasLocationCoordinates(
      BaiduLocation(latitude: 23.1, longitude: 113.3, locType: 0),
      isIOS: false,
    ), isFalse);
  });
}
