import Foundation

@MainActor
class AIService {
    static let shared = AIService()

    private let baseURL = URL(string: "http://100.79.135.75:5000")!

    /// Persistent unique device ID, used as the session ID for the backend.
    private let deviceID: String = {
        if let savedID = UserDefaults.standard.string(forKey: "DeviceID") {
            return savedID
        } else {
            let newID = UUID().uuidString
            UserDefaults.standard.set(newID, forKey: "DeviceID")
            return newID
        }
    }()

    func sendMessage(_ text: String, completion: @escaping (Result<String, Error>) -> Void) {
        print("📱 Sending message: \(text)")
        let url = baseURL.appendingPathComponent("chat")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30.0

        // FIX: The JSON body now includes both 'message' and the required 'session_id'.
        let body: [String: String] = [
            "message": text,
            "session_id": deviceID
        ]
        
        request.httpBody = try? JSONEncoder().encode(body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            print("📱 Received response")
            
            if let error = error {
                print("📱 Error: \(error)")
                completion(.failure(error))
                return
            }

            guard let data = data else {
                print("📱 No data received")
                completion(.failure(NSError(domain: "No data", code: 0)))
                return
            }

            print("📱 Raw response: \(String(data: data, encoding: .utf8) ?? "nil")")

            do {
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let aiResponse = json["response"] as? String {
                    print("📱 Success: \(aiResponse)")
                    completion(.success(aiResponse))
                } else {
                    print("📱 JSON parsing failed")
                    completion(.failure(NSError(domain: "Invalid JSON format", code: 0)))
                }
            } catch {
                print("📱 Exception: \(error)")
                completion(.failure(error))
            }
        }.resume()
    }
}
