function msToReadableTime(ms) {
    let totalSeconds = Math.floor(ms / 1000);

    let hours = Math.floor(totalSeconds / 3600);
    let minutes = Math.floor((totalSeconds % 3600) / 60);
    let seconds = totalSeconds % 60;

    minutes = (minutes < 10) ? "0" + minutes : minutes;
    seconds = (seconds < 10) ? "0" + seconds : seconds;

    let timeString = "";
    if (hours > 0) {
        timeString += hours + ":" + minutes + ":" + seconds;
    } else {
        timeString += minutes + ":" + seconds;
    }

    return timeString;
}

function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

function darkenColor(rgb, percent) {
    return rgb.map(color => Math.max(0, Math.min(255, Math.floor(color * (1 - percent)))));
}

function isDarkColor(rgb) {
    const brightness = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]);
    return brightness < 128;
}

function capitalize(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function formatString(str, ...args) {
    return str.replace(/{(\d+)}/g, (match, number) => typeof args[number] !== 'undefined' ? args[number] : match);
};