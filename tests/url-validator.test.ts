import { describe, it, expect } from "vitest";
import { validateGitHubUrl, isPrivateOrReservedIP, URLValidationError } from "@/lib/repository/url-validator";

describe("URL Validator", () => {
  it("accepts valid GitHub repository URLs", () => {
    const valid = [
      "https://github.com/octocat/Hello-World",
      "https://github.com/octocat/Hello-World.git",
      "https://www.github.com/psf/requests",
      "https://github.com/facebook/react/",
    ];
    for (const url of valid) {
      const res = validateGitHubUrl(url);
      expect(res.provider).toBe("github");
      expect(res.normalizedUrl).toContain(".git");
      expect(res.canonicalIdentity).toContain("/");
    }
  });

  it("rejects non-HTTPS protocols", () => {
    expect(() => validateGitHubUrl("http://github.com/user/repo")).toThrow(URLValidationError);
    expect(() => validateGitHubUrl("ftp://github.com/user/repo")).toThrow(URLValidationError);
  });

  it("rejects embedded credentials", () => {
    expect(() => validateGitHubUrl("https://user:token@github.com/user/repo")).toThrow(URLValidationError);
  });

  it("rejects unexpected ports", () => {
    expect(() => validateGitHubUrl("https://github.com:8080/user/repo")).toThrow(URLValidationError);
  });

  it("rejects localhost and private IPs", () => {
    expect(isPrivateOrReservedIP("127.0.0.1")).toBe(true);
    expect(isPrivateOrReservedIP("10.0.0.1")).toBe(true);
    expect(isPrivateOrReservedIP("192.168.1.1")).toBe(true);
    expect(isPrivateOrReservedIP("169.254.169.254")).toBe(true);
    expect(isPrivateOrReservedIP("8.8.8.8")).toBe(false);

    expect(() => validateGitHubUrl("https://localhost/user/repo")).toThrow(URLValidationError);
    expect(() => validateGitHubUrl("https://127.0.0.1/user/repo")).toThrow(URLValidationError);
  });

  it("rejects reserved GitHub paths", () => {
    expect(() => validateGitHubUrl("https://github.com/settings/profile")).toThrow(URLValidationError);
  });
});
