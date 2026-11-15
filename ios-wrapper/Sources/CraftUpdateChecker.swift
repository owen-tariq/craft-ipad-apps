import UIKit

/// Checks the published GitHub release assets for this particular installed Craft app.
/// This never downloads or installs an IPA without the user's explicit action.
final class CraftUpdateChecker {
    private weak var presenter: UIViewController?
    private var checking = false
    private var lastPromptedVersion: String?

    init(presenter: UIViewController) {
        self.presenter = presenter
    }

    func checkForUpdates() {
        guard !checking,
              let bundleID = Bundle.main.bundleIdentifier,
              let appID = bundleID.split(separator: ".").last else { return }
        checking = true
        let name = String(appID)
        let current = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"
        let endpoint = URL(string: "https://api.github.com/repos/owen-tariq/craft-ipad-apps/releases?per_page=30")!
        var request = URLRequest(url: endpoint, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 12)
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            defer { DispatchQueue.main.async { self?.checking = false } }
            guard error == nil, let http = response as? HTTPURLResponse,
                  (200...299).contains(http.statusCode), let data = data,
                  let releases = (try? JSONSerialization.jsonObject(with: data)) as? [[String: Any]] else { return }

            var newest: (version: String, url: URL)?
            for release in releases where (release["draft"] as? Bool) != true {
                guard let assets = release["assets"] as? [[String: Any]] else { continue }
                for asset in assets {
                    guard let filename = asset["name"] as? String,
                          filename.lowercased().hasPrefix(name.lowercased() + "-v"),
                          filename.lowercased().hasSuffix("-ipad.ipa"),
                          let download = asset["browser_download_url"] as? String,
                          let url = URL(string: download) else { continue }
                    let prefixLength = name.count + 2
                    let suffixLength = "-iPad.ipa".count
                    guard filename.count > prefixLength + suffixLength else { continue }
                    let version = String(filename.dropFirst(prefixLength).dropLast(suffixLength))
                    guard version.split(separator: ".").count == 3,
                          version.split(separator: ".").allSatisfy({ Int($0) != nil }) else { continue }
                    if newest == nil || version.compare(newest!.version, options: .numeric) == .orderedDescending {
                        newest = (version, url)
                    }
                }
            }
            guard let latest = newest,
                  latest.version.compare(current, options: .numeric) == .orderedDescending else { return }
            DispatchQueue.main.async { [weak self] in
                guard let self = self, self.lastPromptedVersion != latest.version,
                      let presenter = self.presenter, presenter.presentedViewController == nil else { return }
                self.lastPromptedVersion = latest.version
                let alert = UIAlertController(
                    title: "Update Available",
                    message: "A new version of \(name.capitalized) is available.\nInstalled: \(current)\nAvailable: \(latest.version)\n\nDownload the new IPA and install it using Feather or your preferred signing app.",
                    preferredStyle: .alert
                )
                alert.addAction(UIAlertAction(title: "Later", style: .cancel))
                alert.addAction(UIAlertAction(title: "Download IPA", style: .default) { _ in
                    UIApplication.shared.open(latest.url)
                })
                presenter.present(alert, animated: true)
            }
        }.resume()
    }
}
