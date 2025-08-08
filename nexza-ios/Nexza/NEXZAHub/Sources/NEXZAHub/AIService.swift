import Foundation

/// `AIService` is a simple network client that posts chat messages to a
/// locally hosted AI service. The service is expected to be reachable
/// over a Tailscale IP address. Update the `baseURL` to point at
/// your AI server before running the app.
@MainActor
class AIService {
    static let shared = AIService()

    /// Replace with your Tailscale IP and port. For example,
    /// `http://100.64.0.1:5000`. This placeholder value should be
    /// customised before using the app.
    private let baseURL = URL(string: "http://100.64.0.1:5000")!

    /// Sends a user message to the AI server. The server is expected to
    /// respond with a string containing the AI's reply. The result is
    /// delivered on a background thread; call site should dispatch to
    /// the main queue if UI updates are needed.
    func sendMessage(_ text: String, completion: @escaping (Result<String, Error>) -> Void) {
        let url = baseURL.appendingPathComponent("chat")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["message": text]
        request.httpBody = try? JSONEncoder().encode(body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            // Propagate any network or encoding error directly.
            if let error = error {
                completion(.failure(error))
                return
            }

            // Ensure the server returned data that can be decoded into a
            // UTF‑8 string. Otherwise, return a generic error.
            guard let data = data,
                  let result = String(data: data, encoding: .utf8) else {
                completion(.failure(NSError(domain: "Invalid response", code: 0)))
                return
            }
            completion(.success(result))
        }.resume()
    }
}
