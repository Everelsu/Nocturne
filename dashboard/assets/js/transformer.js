class DataReader {
    constructor(base64Str) {
        const binaryStr = atob(base64Str);
        const byteArray = Uint8Array.from(binaryStr, (c) => c.charCodeAt(0));
        this.buffer = byteArray.buffer;
        this.view = new DataView(this.buffer);
        this.position = 0;
        this.mark = null;
    }

    get remaining() {
        return this.buffer.byteLength - this.position;
    }

    mark() {
        this.mark = this.position;
    }

    rewind() {
        if (this.mark === null) {
            throw new Error("Cannot rewind buffer without a marker!");
        }
        if (this.mark < 0) {
            throw new Error("Cannot rewind buffer to a negative position!");
        }
        this.position = this.mark;
        this.mark = null;
    }

    readByte() {
        if (this.position >= this.buffer.byteLength) {
            throw new Error("End of buffer");
        }
        const byte = this.view.getUint8(this.position);
        this.position += 1;
        return byte;
    }

    readBoolean() {
        return this.readByte() !== 0;
    }

    readUnsignedShort() {
        if (this.position + 2 > this.buffer.byteLength) {
            throw new Error("End of buffer");
        }
        const value = this.view.getUint16(this.position, false); // big-endian
        this.position += 2;
        return value;
    }

    readInt() {
        if (this.position + 4 > this.buffer.byteLength) {
            throw new Error("End of buffer");
        }
        const value = this.view.getInt32(this.position, false); // big-endian
        this.position += 4;
        return value;
    }

    readLong() {
        if (this.position + 8 > this.buffer.byteLength) {
            throw new Error("End of buffer");
        }
        const value = this.view.getBigUint64(this.position, false); // big-endian
        this.position += 8;
        return value;
    }

    readNullableUtf(utfm = false) {
        const exists = this.readBoolean();
        if (!exists) {
            return null;
        }
        return utfm ? this.readUtfm() : this.readUtf();
    }

    readUtf() {
        const length = this.readUnsignedShort();
        if (this.position + length > this.buffer.byteLength) {
            throw new Error("End of buffer");
        }
        const bytes = new Uint8Array(this.buffer, this.position, length);
        this.position += length;
        const decoder = new TextDecoder("utf-8");
        return decoder.decode(bytes);
    }

    readUtfm() {
        const length = this.readUnsignedShort();
        if (this.position + length > this.buffer.byteLength) {
            throw new Error("End of buffer");
        }
        const bytes = new Uint8Array(this.buffer, this.position, length);
        this.position += length;
        return readUtfm(length, bytes);
    }
}

function decodeProbeInfo(reader) {
    const probeInfo = reader.readUtf();
    return { probe_info: probeInfo };
}

function decodeLavasrcFields(reader) {
    if (reader.remaining <= 8) {
        return {};
    }

    const albumName = reader.readNullableUtf();
    const albumUrl = reader.readNullableUtf();
    const artistUrl = reader.readNullableUtf();
    const artistArtworkUrl = reader.readNullableUtf();
    const previewUrl = reader.readNullableUtf();
    const isPreview = reader.readBoolean();

    return {
        album_name: albumName,
        album_url: albumUrl,
        artist_url: artistUrl,
        artist_artwork_url: artistArtworkUrl,
        preview_url: previewUrl,
        is_preview: isPreview,
    };
}

const DEFAULT_DECODER_MAPPING = {
    http: decodeProbeInfo,
    local: decodeProbeInfo,
    deezer: decodeLavasrcFields,
    spotify: decodeLavasrcFields,
    applemusic: decodeLavasrcFields,
    yandexmusic: decodeLavasrcFields,
    vkmusic: decodeLavasrcFields,
};

function readUtfm(utfLen, utfBytes) {
    const chars = [];
    let count = 0;

    while (count < utfLen) {
        const char = utfBytes[count] & 0xff;
        if (char > 127) {
            break;
        }
        count += 1;
        chars.push(String.fromCharCode(char));
    }

    while (count < utfLen) {
        const char = utfBytes[count] & 0xff;
        const shift = char >> 4;

        if (shift >= 0 && shift <= 7) {
            count += 1;
            chars.push(String.fromCharCode(char));
        } else if (shift >= 12 && shift <= 13) {
            if (count + 2 > utfLen) {
                throw new Error("malformed input: partial character at end");
            }
            const char2 = utfBytes[count + 1];
            if ((char2 & 0xc0) !== 0x80) {
                throw new Error(`malformed input around byte ${count + 1}`);
            }
            const charShift = ((char & 0x1f) << 6) | (char2 & 0x3f);
            chars.push(String.fromCharCode(charShift));
            count += 2;
        } else if (shift === 14) {
            if (count + 3 > utfLen) {
                throw new Error("malformed input: partial character at end");
            }
            const char2 = utfBytes[count + 1];
            const char3 = utfBytes[count + 2];
            if ((char2 & 0xc0) !== 0x80 || (char3 & 0xc0) !== 0x80) {
                throw new Error(`malformed input around byte ${count + 1}`);
            }
            const charShift =
                ((char & 0x0f) << 12) | ((char2 & 0x3f) << 6) | (char3 & 0x3f);
            chars.push(String.fromCharCode(charShift));
            count += 3;
        } else {
            throw new Error(`malformed input around byte ${count}`);
        }
    }
    return chars.join("");
}

function readTrackCommon(reader) {
    const title = reader.readUtfm();
    const author = reader.readUtfm();
    const length = reader.readLong();
    const identifier = reader.readUtf();
    const isStream = reader.readBoolean();
    const uri = reader.readNullableUtf();
    return [title, author, length, identifier, isStream, uri];
}

function decode(trackId, requester, sourceDecoders = {}) {
    const decoders = { ...DEFAULT_DECODER_MAPPING, ...sourceDecoders };
    const reader = new DataReader(trackId);

    const flags = (reader.readInt() & 0xc0000000) >>> 30;
    const version = (flags & 1) !== 0 ? reader.readByte() : 1;

    const [title, author, length, identifier, isStream, uri] =
        readTrackCommon(reader);

    let extraFields = {};
    if (version === 3) {
        extraFields.artworkUrl = reader.readNullableUtf();
        extraFields.isrc = reader.readNullableUtf();
    }

    const source = reader.readUtf();

    let sourceSpecificFields = {};
    if (source in decoders) {
        sourceSpecificFields = decoders[source](reader);
    }

    const position = reader.readLong();

    return new Track({
        trackId,
        title,
        author,
        length: parseInt(length),
        identifier,
        isStream,
        uri,
        isSeekable: !isStream,
        source: source,
        position: parseInt(position),
        ...extraFields,
    }, requester);
}
