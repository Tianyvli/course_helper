# 课程助手 1.2.0：iOS 未签名构建

源码基于上游 v1.2.0，提交 `900ed39b05dcec2386a14a2a636eaceb2173d68a`。
保留原始版权和 LICENSE；此构建没有经过 iPhone 真机功能验证。

## 获取 IPA

在仓库 Actions 页面选择 **Build unsigned iOS IPA**，打开成功的运行，
下载 **CourseHelper_1.2.0_unsigned** 附件并解压。
包含 IPA、SHA-256 校验值、源码与工具链信息、依赖锁文件，保留 30 天。
推送 `ios-unsigned` 分支会触发构建。若 Fork 中 Actions 尚未启用，先在网页启用。
GitHub 的手动运行按钮要求此工作流也存在于默认分支；需要时将本分支合入默认分支。

## 签名与安装

`CourseHelper_1.2.0_unsigned.ipa` 是供 iPhone 使用的 arm64 应用，未签名，不能直接安装。
使用你已有的签名工具（例如支持本机系统的 Sideloadly 或 AltStore）导入 IPA，
通过该工具完成 Apple 账号登录、签名和安装。不要将 Apple 密码或证书提交到仓库。
有效期、设备限制及开发者模式要求以所选签名方式和 iOS 提示为准。
本工作流不申请证书、不创建 TestFlight 或 App Store 发布。

## 百度地图和定位

iOS 默认使用上游 Info.plist 中原有的公开 SDK key，并在 Dart 中调用地图和定位鉴权接口。
该 key 是否绑定 `com.anerycoft.coursehelper` 尚未验证。定位或地图鉴权失败时，
需要在百度地图开放平台为最终签名后的 Bundle ID 配置 iOS key。
将 key 设置为仓库 Actions variable `BAIDU_IOS_MAP_AK` 后重新构建。
签名工具如果改写 Bundle ID，也需确保它与百度地图 key 的绑定一致。
key 会嵌入客户端，属于 SDK 客户端配置，不能作为服务端密钥使用。

## 功能验收

签名安装后分别验证：

- 首次启动、重启后的账号保存，以及学习通/雨课堂登录和切换。
- 课程列表、各类签到、扫码、定位，以及相机/定位权限拒绝后的重试。
- 相册选择图片、二维码图片识别、PPT 图片保存。
- 课堂交互、应用前台收到活动时的通知。
- 切换后台、锁屏、再回到应用后的连接恢复情况。

现有业务请求和数据格式保持不变。iOS 后台调度由系统决定；本地通知和后台任务
不等同于 APNs 推送，不保证锁屏后的即时消息或持续 WebSocket 连接。
未配置 APNs 服务、第三方服务器或任何后台保活绕过机制。

## 本地 macOS 构建

使用 Xcode 16.4、Flutter 3.41.8、Python 3.13 和 CocoaPods：

```sh
flutter pub get --enforce-lockfile
flutter build ios --config-only --release --no-codesign
(cd ios && pod install --repo-update)
flutter build ios --release --no-codesign --no-pub --build-name=1.2.0 --build-number=1
python3 scripts/package_unsigned_ipa.py
(cd dist && shasum -a 256 -c CourseHelper_1.2.0_unsigned.ipa.sha256)
```

以构建附件记录的 `minimum_ios` 字段为最低系统版本；原生插件兼容性以实际构建结果为准。
