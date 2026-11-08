// Parses a .vcf file with Apple's Contacts framework and prints each contact as
// KEY=value lines followed by "---". Used by tests/test_vcard.py to check that
// the cards Humanize writes import cleanly into macOS and iOS Contacts.
//
//   swift tests/parse_vcard.swift card.vcf
import Contacts
import Foundation

let args = CommandLine.arguments
guard args.count == 2, let data = FileManager.default.contents(atPath: args[1]) else {
    FileHandle.standardError.write("usage: swift parse_vcard.swift <file.vcf>\n".data(using: .utf8)!)
    exit(2)
}

do {
    let contacts = try CNContactVCardSerialization.contacts(with: data)
    for c in contacts {
        print("GN=\(c.givenName)")
        print("FN=\(c.familyName)")
        print("TITLE=\(c.jobTitle)")
        for p in c.phoneNumbers { print("TEL=\(p.value.stringValue)") }
        for e in c.emailAddresses { print("EMAIL=\(e.value as String)") }
        print("---")
    }
} catch {
    FileHandle.standardError.write("parse failed: \(error)\n".data(using: .utf8)!)
    exit(1)
}
