# Security Policy

## 🔒 Overview

We take the security of the Data Science Agent project seriously. This document outlines our security policy, how to report vulnerabilities, and our security practices.

---

## 🛡️ Supported Versions

We currently support the following versions with security updates:

| Version | Supported          | End of Support |
| ------- | ------------------ | -------------- |
| 1.0.x   | ✅ Yes             | TBD            |
| < 1.0   | ❌ No              | 2025-01-15     |

---

## 🚨 Reporting a Vulnerability

### How to Report

If you discover a security vulnerability, please **DO NOT** open a public issue. Instead:

1. **Email**: Send details to security@example.com
2. **GitHub Security**: Use GitHub's [Security Advisory](https://github.com/yourusername/data-science-agent/security/advisories/new) feature
3. **PGP**: Use our PGP key (available at keybase.io/projectname) for sensitive information

### What to Include

Please include the following in your report:

- **Description**: Clear description of the vulnerability
- **Impact**: Potential impact and severity
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Proof of Concept**: Code or commands demonstrating the vulnerability
- **Environment**: OS, Python version, dependencies
- **Suggested Fix**: If you have one (optional)

### Example Report

```
Subject: [SECURITY] SQL Injection in data loading function

Description:
The load_dataframe function in ds_tools.py is vulnerable to SQL injection
when loading data from database connections.

Impact:
An attacker could execute arbitrary SQL commands, potentially accessing
or modifying sensitive data.

Steps to Reproduce:
1. Upload a CSV with malicious SQL in column names
2. Call load_dataframe() on the file
3. Observe SQL execution

Environment:
- OS: Ubuntu 22.04
- Python: 3.12.0
- Version: 1.0.0

Suggested Fix:
Use parameterized queries instead of string concatenation.
```

---

## 🕐 Response Timeline

We aim to respond to security reports as follows:

| Timeframe | Action |
|-----------|--------|
| **24 hours** | Initial acknowledgment |
| **72 hours** | Initial assessment and severity rating |
| **7 days** | Detailed response and timeline |
| **30 days** | Patch release (for critical vulnerabilities) |

### Severity Levels

- **Critical**: Immediate risk, patch within 7 days
- **High**: Significant risk, patch within 30 days
- **Medium**: Moderate risk, patch within 90 days
- **Low**: Minor risk, patch in next release

---

## 🔐 Security Best Practices

### For Users

#### API Key Security

✅ **DO:**
- Store API keys in environment variables
- Use `.env` files (never commit to git)
- Rotate keys regularly
- Use separate keys for dev/prod

❌ **DON'T:**
- Hard-code API keys in code
- Share keys in public channels
- Use production keys in development
- Commit keys to version control

#### Data Security

✅ **DO:**
- Sanitize sensitive data before uploading
- Use private networks for sensitive data
- Regularly review uploaded files
- Delete old/unused data

❌ **DON'T:**
- Upload PII without anonymization
- Use production data in testing
- Share sensitive datasets publicly
- Ignore data retention policies

### For Developers

#### Code Security

✅ **DO:**
- Validate all user inputs
- Use parameterized queries
- Implement rate limiting
- Keep dependencies updated
- Use type hints and validation
- Log security events

❌ **DON'T:**
- Trust user input
- Use `eval()` or `exec()`
- Expose internal paths
- Ignore security warnings
- Use deprecated libraries

#### Dependency Security

```bash
# Regularly update dependencies
uv sync --upgrade

# Check for vulnerabilities
pip install safety
safety check

# Audit dependencies
pip-audit
```

---

## 🛠️ Security Features

### Current Security Measures

1. **Input Validation**
   - File type checking
   - Size limits enforcement
   - Path traversal prevention
   - Formula injection detection

2. **Data Protection**
   - PII hashing in logs
   - Secure file handling
   - Temporary file cleanup
   - Access control

3. **API Security**
   - Environment variable-based auth
   - Rate limiting (via LiteLLM)
   - Request validation
   - Error message sanitization

4. **Code Security**
   - Runtime validation
   - Syntax checking
   - Import verification
   - Type safety

---

## 🔍 Known Security Considerations

### OpenAI API Key

- **Risk**: API key exposure could lead to unauthorized usage
- **Mitigation**: Use environment variables, never commit keys
- **Monitoring**: Monitor API usage in OpenAI dashboard

### File Uploads

- **Risk**: Malicious files could exploit parsing vulnerabilities
- **Mitigation**: File type validation, size limits, sanitization
- **Monitoring**: Log all file operations

### Model Persistence

- **Risk**: Malicious models could execute arbitrary code
- **Mitigation**: Store models in secure directory, validate on load
- **Monitoring**: Track model creation and loading

### LLM Prompt Injection

- **Risk**: Malicious prompts could bypass safety measures
- **Mitigation**: Input validation, output filtering, rate limiting
- **Monitoring**: Log suspicious patterns

---

## 📋 Security Checklist

### Before Deployment

- [ ] Remove all hard-coded secrets
- [ ] Set up environment variables
- [ ] Enable HTTPS
- [ ] Configure firewall rules
- [ ] Set up logging and monitoring
- [ ] Review file permissions
- [ ] Update all dependencies
- [ ] Run security scanner
- [ ] Test backup and recovery
- [ ] Document security procedures

### Regular Maintenance

- [ ] Review access logs (weekly)
- [ ] Update dependencies (monthly)
- [ ] Rotate API keys (quarterly)
- [ ] Security audit (quarterly)
- [ ] Penetration testing (annually)
- [ ] Review security policies (annually)

---

## 🔄 Vulnerability Disclosure Process

### Our Process

1. **Reception**: We receive your security report
2. **Acknowledgment**: We confirm receipt within 24 hours
3. **Assessment**: We evaluate severity and impact
4. **Development**: We create and test a fix
5. **Release**: We release a security patch
6. **Disclosure**: We publicly disclose (coordinated)

### Coordinated Disclosure

We believe in responsible disclosure:

1. **Private reporting**: Report vulnerabilities privately first
2. **Fix development**: Allow time for us to develop a fix
3. **Patch release**: We release a patch to users
4. **Public disclosure**: After patch is available (typically 90 days)

### Credit

We will credit security researchers who:
- Report vulnerabilities responsibly
- Follow coordinated disclosure
- Help us improve security

Your name will appear in:
- Security advisories
- Release notes
- CONTRIBUTORS.md
- Security acknowledgments

---

## 🏆 Security Acknowledgments

We thank the following researchers for responsible disclosure:

<!-- This section will be populated as vulnerabilities are reported and fixed -->

| Date | Researcher | Vulnerability | Severity |
|------|-----------|---------------|----------|
| TBD  | TBD       | TBD           | TBD      |

---

## 📚 Security Resources

### External Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)

### Tools

- [Bandit](https://bandit.readthedocs.io/) - Python security linter
- [Safety](https://pyup.io/safety/) - Dependency vulnerability scanner
- [pip-audit](https://github.com/pypa/pip-audit) - Dependency auditing
- [Trivy](https://github.com/aquasecurity/trivy) - Container security scanner

---

## 🔐 Encryption & Privacy

### Data in Transit

- Use HTTPS for all web communications
- TLS 1.2+ for API calls
- Encrypted environment variables

### Data at Rest

- Models stored locally (not transmitted)
- User data remains on user's machine
- No telemetry without consent

### Privacy Policy

- We do not collect personal data
- API calls go directly to OpenAI
- Local execution, no external storage
- User data never leaves their control

---

## 📞 Contact

For security concerns:

- **Email**: security@example.com
- **PGP Key**: Available at keybase.io/projectname
- **GitHub Security**: Use Security Advisories feature
- **Response Time**: 24 hours for acknowledgment

For non-security issues:
- Use GitHub Issues
- Join our Discord
- Email: support@example.com

---

## 📝 Security Updates

Subscribe to security updates:

- **GitHub Watch**: Enable "Security alerts only"
- **Mailing List**: security-announce@example.com
- **RSS Feed**: /security.rss
- **Twitter**: @projectname

---

## ✅ Compliance

We strive to comply with:

- GDPR (data protection)
- SOC 2 Type II (if applicable)
- ISO 27001 (information security)
- OWASP ASVS (application security)

---

## 🔄 Policy Updates

This security policy may be updated periodically. Check back regularly or watch for updates:

**Last Updated**: 2025-01-15  
**Version**: 1.0  
**Next Review**: 2025-07-15

---

<div align="center">

**🔒 Security is everyone's responsibility. Thank you for helping keep our project safe! 🔒**

</div>

---

## 📄 License

This security policy is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

