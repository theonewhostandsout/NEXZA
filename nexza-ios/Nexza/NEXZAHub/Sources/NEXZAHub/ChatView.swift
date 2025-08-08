import SwiftUI

/// `ChatView` presents a scrolling conversation between the user and the AI
/// service. It allows the user to enter messages and handles sending
/// requests via `AIService`.
struct ChatView: View {
    @StateObject private var history = ChatHistory()
    @State private var currentMessage: String = ""
    @State private var isSending: Bool = false

    var body: some View {
        VStack {
            ScrollViewReader { proxy in
                ScrollView {
                    ForEach(history.messages) { message in
                        HStack {
                            if message.isUser {
                                Spacer()
                            }
                            Text(message.text)
                                .padding()
                                .background(message.isUser ? Color.blue.opacity(0.6) : Color.gray.opacity(0.3))
                                .foregroundColor(.white)
                                .cornerRadius(12)
                                .frame(maxWidth: UIScreen.main.bounds.width * 0.7, alignment: message.isUser ? .trailing : .leading)
                            if !message.isUser {
                                Spacer()
                            }
                        }
                        // Use the message's id as the scroll id.
                        .id(message.id)
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 4)
                    .onChange(of: history.messages.count) { _ in
                        // Scroll to the last message whenever a new one is appended.
                        if let last = history.messages.last {
                            withAnimation {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                }
            }

            Divider()

            HStack {
                TextField("Message", text: $currentMessage)
                    .textFieldStyle(.roundedBorder)
                Button(action: sendMessage) {
                    if isSending {
                        ProgressView()
                    } else {
                        Image(systemName: "paperplane.fill")
                    }
                }
                .disabled(currentMessage.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSending)
            }
            .padding()
            .background(Color.black.opacity(0.8))
        }
    }

    /// Sends the current message to the AI service and appends responses.
    private func sendMessage() {
        let trimmed = currentMessage.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        // Append the user's message and clear the input field.
        history.addMessage(ChatMessage(text: trimmed, isUser: true))
        currentMessage = ""
        isSending = true
        AIService.shared.sendMessage(trimmed) { result in
            DispatchQueue.main.async {
                isSending = false
                switch result {
                case .success(let reply):
                    history.addMessage(ChatMessage(text: reply, isUser: false))
                case .failure(let error):
                    history.addMessage(ChatMessage(text: "Error: \(error.localizedDescription)", isUser: false))
                }
            }
        }
    }
}

/// Preview provider for design‑time rendering in Xcode.
struct ChatView_Previews: PreviewProvider {
    static var previews: some View {
        ChatView()
            .preferredColorScheme(.dark)
    }
}