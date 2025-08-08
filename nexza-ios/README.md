# NEXZA iOS App

## Overview
The NEXZA iOS App is a SwiftUI-based mobile client for the NEXZA AI Assistant platform.
It connects to the backend API to deliver real-time AI responses, chat history, and user authentication.

## Features
- **SwiftUI Interface**: Modern, responsive design.
- **Real-Time Chat**: Connects to backend API for AI-driven conversations.
- **User Authentication**: Login and session management.
- **Cross-Platform Ready**: Built with scalability in mind.

## Requirements
- Xcode 15+
- iOS 16+

## Setup
1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/nexza-ios.git
    cd nexza-ios
    ```
2. Open the project in Xcode:
    ```bash
    open Nexza.xcodeproj
    ```
3. Update API endpoint constants in `AIService.swift`.
4. Build and run on a simulator or device.

## Project Structure
- `ContentView.swift` - Main entry UI.
- `ChatView.swift` - Chat interface.
- `LoginView.swift` - Authentication screen.
- `AIService.swift` - Handles API calls to backend.
- `Assets.xcassets` - Image and color resources.

## Security
Ensure no API keys or sensitive constants are hardcoded in Swift files.

## License
MIT License
