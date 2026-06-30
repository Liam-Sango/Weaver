import hashlib
import hmac
import PIL.Image
import numpy

#Converts a bytes object into a flat list of bits, MSB first per byte
def bytes_to_bits(data: bytes) -> list[int]:
    bit_list = []

    for x in range(len(data)):
        byte_value = data[x]

        for position in range(7, -1, -1):
            bit = (byte_value >> position) & 1
            bit_list.append(bit)

    return bit_list

#Converts a flat list of bits back into bytes, MSB first per byte
def bits_to_bytes(bits: list[int]) -> bytes:
    byte_values = []

    for x in range(len(bits) // 8):
        byte_chunk = 0

        for i in range(8):
            byte_chunk = (byte_chunk << 1) | bits[(x * 8) + i]

        byte_values.append(byte_chunk)

    finished_bytes = bytes(byte_values)
    return finished_bytes

#Generates a deterministic shuffled sequence of pixel positions seeded by k_extract
def generate_positions(image_shape: tuple, k_extract: bytes, num_positions: int) -> list[tuple]:
    height, width, channels = image_shape
    total_positions = height * width * channels

    if num_positions > total_positions:
        raise ValueError(
            f"Requested {num_positions} positions but image only has {total_positions}."
        )

    #Derives a fixed-length seed from k_extract via SHA-256 so any key length works
    seed_bytes = hashlib.sha256(k_extract).digest()

    #Generates unique positions using HMAC-SHA256 in counter mode as a CSPRNG
    used = set()
    positions = []
    counter = 0

    while len(positions) < num_positions:
        counter_bytes = counter.to_bytes(8, "big")
        index_bytes = hmac.new(seed_bytes, counter_bytes, hashlib.sha256).digest()
        index = int.from_bytes(index_bytes, "big") % total_positions
        counter += 1

        if index in used:
            continue
        used.add(index)

        #Maps a flat index to (x, y, channel) coordinates
        n = index
        channel = n % 3
        n = n // 3
        x = n % width
        y = n // width
        positions.append((x, y, channel))

    return positions

#Embeds a payload into the LSBs of a cover image at keyed positions
def embed(cover_image_path: str, payload: bytes, k_extract: bytes) -> PIL.Image:
    image = PIL.Image.open(cover_image_path).convert("RGB")
    pixels = numpy.array(image, dtype=numpy.uint8)

    length_prefix = len(payload).to_bytes(4, "big")
    full_payload = length_prefix + payload

    bits = bytes_to_bits(full_payload)
    positions = generate_positions(pixels.shape, k_extract, len(bits))

    #Writes each payload bit into the LSB of the target pixel channel
    for bit, (x, y, channel) in zip(bits, positions):
        pixels[y, x, channel] = (pixels[y, x, channel] & 0xFE) | bit

    return PIL.Image.fromarray(pixels)

#Extracts a payload from the LSBs of a stego image at keyed positions
def extract(stego_image_path: str, k_extract: bytes) -> bytes:
    image = PIL.Image.open(stego_image_path).convert("RGB")
    pixels = numpy.array(image, dtype=numpy.uint8)

    #Generates positions for the 4-byte length prefix plus the payload
    prefix_positions = generate_positions(pixels.shape, k_extract, 32)
    prefix_bits = []
    for (x, y, channel) in prefix_positions:
        prefix_bits.append(int(pixels[y, x, channel] & 1))

    prefix_bytes = bits_to_bytes(prefix_bits)
    payload_length = int.from_bytes(prefix_bytes, "big")

    #Generates positions for the full payload (prefix + payload) and skips the first 32
    total_bits = 32 + payload_length * 8
    all_positions = generate_positions(pixels.shape, k_extract, total_bits)

    #Reads the LSB of each selected pixel channel to collect payload bits
    payload_bits = []
    for (x, y, channel) in all_positions[32:]:
        payload_bits.append(int(pixels[y, x, channel] & 1))

    return bits_to_bytes(payload_bits)

