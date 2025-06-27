function copyInviteCode() {
    const code = document.getElementById('invite-code').innerText;
    navigator.clipboard.writeText(code);
}
