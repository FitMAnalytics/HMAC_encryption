import re
import hmac
import hashlib

def tokenize_address(text, language='zh'):
    """
    Tokenize address text into meaningful units.
    
    - Numbers (sequences of digits) are kept as atomic tokens
    - For English: split on whitespace, then further split non-numeric parts into chars
    - For Chinese: each character is a token (except numbers, kept whole)
    
    Examples:
        'flat 12b main st' -> ['f','l','a','t','12','b','m','a','i','n','s','t']
        '北京市朝阳区123号' -> ['北','京','市','朝','阳','区','123','号']
    """
    # Normalize
    clean_text = " ".join(text.split()).strip().lower()
    
    if language == 'zh':
        # For Chinese: split into chars but keep digit runs together
        tokens = re.findall(r'\d+|.', clean_text)
        tokens = [t for t in tokens if not t.isspace()]
    elif language == 'en':
        # For English: keep digit runs and letter runs as units,
        # then split letter runs into individual chars
        raw_tokens = re.findall(r'\d+|[a-z]+|[^a-z0-9\s]', clean_text)
        tokens = []
        for tok in raw_tokens:
            if re.match(r'^\d+$', tok):
                tokens.append(tok)        # number: atomic
            else:
                tokens.extend(list(tok))  # letters/symbols: char-level
    
    else:
        print("Input language is not supported.")
        return []

    return tokens

def get_hmac_1grams(
    tokens, 
    secret_key="dia-123", 
    truncate_switch = False, 
    truncate_length = 12
    ):

    key_bytes = secret_key.encode('utf-8')
    
    hmac_list = []
    
    for char in tokens:
        h = hmac.new(key_bytes, char.encode('utf-8'), hashlib.sha256)
        if truncate_switch:
            hmac_list.append(h.hexdigest()[:truncate_length])
        else:
            hmac_list.append(h.hexdigest())
        
    return hmac_list    

def get_hmac_2grams(
    tokens, 
    secret_key="dia-123",
    pad_switch=True, 
    truncate_switch=False, 
    truncate_length=12
    ):
    # 1. Normalization
    key_bytes = secret_key.encode('utf-8')
    
    # 2. Add special start/end tokens
    if pad_switch:
        padded_text = ["<S>"] + tokens + ["<E>"]
    else:
        padded_text = tokens
    
    hmac_list = []
    
    # 3. Slide over consecutive pairs
    for i in range(len(padded_text) - 1):
        bigram = padded_text[i] + padded_text[i + 1]
        h = hmac.new(key_bytes, bigram.encode('utf-8'), hashlib.sha256)
        if truncate_switch:
            hmac_list.append(h.hexdigest()[:truncate_length])
        else:
            hmac_list.append(h.hexdigest())
        
    return hmac_list

def levenshtein_hmac(list_a, list_b):
    """
    Calculates the Levenshtein distance between two lists of HMAC hashes.
    """
    size_a = len(list_a)
    size_b = len(list_b)
    
    # Initialize the distance matrix
    # Rows represent list_a, Columns represent list_b
    matrix = [[0] * (size_b + 1) for _ in range(size_a + 1)]

    # Fill the first row and column (base cases for empty strings)
    for i in range(size_a + 1):
        matrix[i][0] = i
    for j in range(size_b + 1):
        matrix[0][j] = j

    # Compute the edit distance
    for i in range(1, size_a + 1):
        for j in range(1, size_b + 1):
            # If the hashes match, the cost is 0
            if list_a[i-1] == list_b[j-1]:
                cost = 0
            else:
                cost = 1
            
            matrix[i][j] = min(
                matrix[i-1][j] + 1,      # Deletion
                matrix[i][j-1] + 1,      # Insertion
                matrix[i-1][j-1] + cost  # Substitution
            )

    return matrix[size_a][size_b]

def jaro_similarity_hmac(list_a, list_b):
    len_a, len_b = len(list_a), len(list_b)
    if len_a == 0 or len_b == 0:
        return 0.0

    # Maximum distance for a "match"
    match_distance = max(len_a, len_b) // 2 - 1
    
    matches_a = [False] * len_a
    matches_b = [False] * len_b
    
    m = 0
    # Find matching characters within the allowed distance
    for i in range(len_a):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len_b)
        for j in range(start, end):
            if not matches_b[j] and list_a[i] == list_b[j]:
                matches_a[i] = True
                matches_b[j] = True
                m += 1
                break
                
    if m == 0:
        return 0.0

    # Count transpositions
    t = 0
    k = 0
    for i in range(len_a):
        if matches_a[i]:
            while not matches_b[k]:
                k += 1
            if list_a[i] != list_b[k]:
                t += 1
            k += 1
    
    transpositions = t // 2
    
    # Calculate Jaro Score
    return (1/3) * (m/len_a + m/len_b + (m - transpositions)/m)

def jaro_winkler_hmac(list_a, list_b, p=0.1):
    # 1. Get the base Jaro similarity
    j_score = jaro_similarity_hmac(list_a, list_b)
    
    # 2. Calculate prefix length (l) up to 4 characters
    l = 0
    max_prefix = min(len(list_a), len(list_b), 4)
    
    for i in range(max_prefix):
        if list_a[i] == list_b[i]:
            l += 1
        else:
            break
            
    # 3. Apply the Winkler modification
    w_score = j_score + (l * p * (1 - j_score))
    
    return w_score

def get_qgrams_from_hash_list(hash_list, q=2, padded=True):
    """
    Groups a list of 1-gram hashes into q-gram tuples.
    Input: ['hash1', 'hash2', 'hash3']
    Output (q=2, padded=True): [('#', 'hash1'), ('hash1', 'hash2'), ('hash2', 'hash3'), ('hash3', '#')]
    """
    processed_list = list(hash_list)
    
    # 1. Apply padding using a unique sentinel for the 'hash' space
    if padded:
        # We use a non-hex string or a specific sentinel to represent the pad
        pad_token = ["#PAD#"] * (q - 1)
        processed_list = pad_token + processed_list + pad_token
    
    qgram_list = []
    
    # 2. Sliding window over the hash IDs
    for i in range(len(processed_list) - q + 1):
        # We store as a tuple because tuples are hashable (can be used in Counter/Sets)
        qgram_tuple = tuple(processed_list[i:i+q])
        qgram_list.append(qgram_tuple)
        
    return qgram_list

def calculate_qgram_similarity(qgram_list_a, qgram_list_b, denominator_type="average"):
    """
    Calculates similarity between two pre-generated q-gram lists using multiset logic.
    
    Parameters:
    - qgram_list_a, qgram_list_b: Lists of q-gram hashes or tuples.
    - denominator_type: 'longer', 'shorter', or 'average' (Sørensen–Dice).
    """
    if not qgram_list_a or not qgram_list_b:
        return 0.0

    # 1. Convert lists to multisets (Counters) to track frequencies
    counter_a = Counter(qgram_list_a)
    counter_b = Counter(qgram_list_b)
    
    # 2. Find the size of the intersection (sum of min counts for each shared q-gram)
    # The & operator on Counters returns the intersection multiset
    intersection_size = sum((counter_a & counter_b).values())
    
    len_a = len(qgram_list_a)
    len_b = len(qgram_list_b)

    # 3. Apply the chosen denominator logic
    if denominator_type == "longer":
        denominator = max(len_a, len_b)
    elif denominator_type == "shorter":
        denominator = min(len_a, len_b)
    elif denominator_type == "average":
        # This is the Sørensen–Dice denominator
        denominator = (len_a + len_b) / 2
    else:
        raise ValueError("Invalid denominator_type. Choose 'longer', 'shorter', or 'average'.")

    return intersection_size / denominator

def calculate_jaccard(set1, set2):
    """Calculates Jaccard Similarity between two sets of hashes."""
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0

