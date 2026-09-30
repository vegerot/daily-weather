#!/usr/bin/env swift
import AppKit
import CoreLocation
import UserNotifications

let args = CommandLine.arguments
let output = URL(fileURLWithPath: args[2])
func finish(_ value: [String: Any]) {
    try! JSONSerialization.data(withJSONObject: value).write(to: output, options: .atomic)
    NSApplication.shared.terminate(nil)
}
class Delegate: NSObject, NSApplicationDelegate, CLLocationManagerDelegate, UNUserNotificationCenterDelegate {
    let manager = CLLocationManager()
    func applicationDidFinishLaunching(_ notification: Notification) {
        if args[1] == "location" {
            manager.delegate = self
            manager.desiredAccuracy = kCLLocationAccuracyKilometer
            manager.requestWhenInUseAuthorization()
            manager.startUpdatingLocation()
        } else {
            let center = UNUserNotificationCenter.current()
            center.delegate = self
            center.requestAuthorization(options: [.alert, .sound]) { granted, error in
                guard granted else { DispatchQueue.main.async { finish(["error": error?.localizedDescription ?? "Enable Daily Weather notifications in System Settings."]) }; return }
                let content = UNMutableNotificationContent()
                content.title = "Daily Weather"
                content.body = args[3]
                content.sound = .default
                let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
                center.add(request) { error in
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                        finish(error.map { ["error": $0.localizedDescription] } ?? ["ok": true])
                    }
                }
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 90) { finish(["error": "Timed out. Check Location Services and notification permissions for Daily Weather."]) }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last, location.horizontalAccuracy >= 0,
              abs(location.timestamp.timeIntervalSinceNow) < 300 else { return }
        manager.stopUpdatingLocation()
        finish(["latitude": location.coordinate.latitude, "longitude": location.coordinate.longitude])
    }
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        if (error as? CLError)?.code == .locationUnknown { return }
        finish(["error": error.localizedDescription])
    }
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler handler: @escaping (UNNotificationPresentationOptions) -> Void) {
        handler([.banner, .sound, .list])
    }
}
let app = NSApplication.shared
let delegate = Delegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
