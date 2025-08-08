import SwiftUI

/// The entry point of the NEXZA Hub app when built as an iOS application.
/// Uses an `@AppStorage` property to persist the login state and shows
/// either the chat or login view accordingly. The dark color scheme is
/// enforced throughout the app.
@main
struct NexzaHubApp: App {
    @AppStorage("loggedIn") private var loggedIn: Bool = false

    var body: some Scene {
        WindowGroup {
            if loggedIn {
                ChatView()
                    .preferredColorScheme(.dark)
            } else {
                LoginView()
                    .preferredColorScheme(.dark)
            }
        }
    }
}