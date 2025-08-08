import Foundation
import SwiftUI

/// A single message in a chat conversation. Each message has a unique
/// identifier, its text content and a flag indicating whether it was
/// authored by the user (`isUser`) or by the AI service.
struct ChatMessage: Identifiable, Codable {
    let id: UUID = UUID()
    let text: String
    let isUser: Bool
}