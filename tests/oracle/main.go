// Command oracle runs the hstspreload.org header checker on header values.
//
// It reads a JSON array of header values on standard input, each one its octets in hex so
// that octets which are not UTF-8 reach the checker unchanged, and writes, for each value,
// the policy the checker parsed and the codes of its errors and warnings, as a JSON array.
// tests/test_oracle_hstspreload.py drives it; see CONTRIBUTING.md to build it.
package main

import (
	"encoding/hex"
	"encoding/json"
	"os"

	"github.com/chromium/hstspreload"
)

type verdict struct {
	MaxAge            *uint64  `json:"max_age"`
	IncludeSubDomains bool     `json:"include_subdomains"`
	Preload           bool     `json:"preload"`
	Errors            []string `json:"errors"`
	Warnings          []string `json:"warnings"`
}

func codes(issues []hstspreload.Issue) []string {
	out := []string{}
	for _, issue := range issues {
		out = append(out, string(issue.Code))
	}
	return out
}

func main() {
	var values []string
	if err := json.NewDecoder(os.Stdin).Decode(&values); err != nil {
		os.Stderr.WriteString(err.Error() + "\n")
		os.Exit(2)
	}
	out := make([]verdict, 0, len(values))
	for _, encoded := range values {
		octets, err := hex.DecodeString(encoded)
		if err != nil {
			os.Stderr.WriteString(err.Error() + "\n")
			os.Exit(2)
		}
		value := string(octets)
		header, _ := hstspreload.ParseHeaderString(value)
		issues := hstspreload.PreloadableHeaderString(value)
		v := verdict{
			IncludeSubDomains: header.IncludeSubDomains,
			Preload:           header.Preload,
			Errors:            codes(issues.Errors),
			Warnings:          codes(issues.Warnings),
		}
		if header.MaxAge != nil {
			seconds := header.MaxAge.Seconds
			v.MaxAge = &seconds
		}
		out = append(out, v)
	}
	if err := json.NewEncoder(os.Stdout).Encode(out); err != nil {
		os.Exit(2)
	}
}
