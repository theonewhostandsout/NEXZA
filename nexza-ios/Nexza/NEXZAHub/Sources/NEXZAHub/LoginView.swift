import SwiftUI

/// `LoginView` presents a simple sign‑in interface with email and password
/// fields. It stores a boolean flag in `AppStorage` to determine whether
/// the user has logged in and conditionally shows the chat view.
struct LoginView: View {
    @AppStorage("loggedIn") private var loggedIn: Bool = false
    @State private var email: String = ""
    @State private var password: String = ""

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            Text("NEXZA Hub")
                .font(.largeTitle.bold())
                .foregroundColor(.white)
            TextField("Email", text: $email)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .padding()
                .background(Color.gray.opacity(0.2))
                .cornerRadius(8)
                .foregroundColor(.white)
            SecureField("Password", text: $password)
                .padding()
                .background(Color.gray.opacity(0.2))
                .cornerRadius(8)
                .foregroundColor(.white)
            Button(action: { loggedIn = true }) {
                Text("Login")
                    .frame(maxWidth: .infinity)
            }
            .padding()
            .background(Color.blue)
            .foregroundColor(.white)
            .cornerRadius(8)
            Button(action: { loggedIn = true }) {
                Text("Skip for Now")
                    .foregroundColor(.blue)
            }
            Spacer()
        }
        .padding()
        .background(Color.black.ignoresSafeArea())
    }
}

struct LoginView_Previews: PreviewProvider {
    static var previews: some View {
        LoginView()
            .preferredColorScheme(.dark)
    }
}