# This file is part of the Python aiocoap library project.
#
# Copyright (c) 2012-2014 Maciej Wasilak <http://sixpinetrees.blogspot.com/>,
#               2013-2014 Christian Amsüss <c.amsuess@energyharvesting.at>
#
# aiocoap is free software, this file is published under the MIT license as
# described in the accompanying LICENSE file.
#
# Parts of this file (the C code) are Copyright OpenSSL (2013-2016) and
# licensed under the terms of the OpenSSL license; see
# http://www.openssl.org/source/license.html for details

r"""This module contains cryptographic helpers for OSCOAP

The module should be abandoned as soon as the functions can be replaced with
ones from established cryptographic library bindings.

>>> #FIXME move this into a unit test instead of a docstring (because it's only
>>> # test not documentation), and verify it instead of just freezing what the
>>> # output of when i first ran this was
>>> key = b"0123456789----------0123456789--"
>>> iv = b"1234567"
>>> message = b"Hello Bob, this is Alice."
>>> aad = b"The envelope said that this is from Alice to Bob."
>>> ciphertext, tag = encrypt_ccm(message, aad, key, iv, 14)
>>> ciphertext, tag
(b'g^\xc9X\xednx\xd5\xc6\xab\x8c\x85\xaa\xed\\f\xee\xebk\xbc]SCZ\x85', b'P\xce0{K\xaf*\xf9\xb1\xb4\xbc\x1c\x84_')
>>> decrypt_ccm(ciphertext, aad, tag, key, iv)
b'Hello Bob, this is Alice.'
>>> decrypt_ccm(ciphertext, b"The envelope said this is from Michelle to Bob.", tag, key, iv)
Traceback (most recent call last):
  ...
crypto.InvalidAEAD
"""

import cffi

_FFI = cffi.FFI()

# from https://wiki.openssl.org/index.php/EVP_Authenticated_Encryption_and_Decryption

ccm_code = '''
#include <openssl/evp.h>

int encryptccm(unsigned const char *plaintext, int plaintext_len, unsigned const char *aad,
	int aad_len, unsigned const char *key, unsigned const char *iv,
	unsigned char *ciphertext, unsigned char *tag, int tag_len)
{
	EVP_CIPHER_CTX *ctx;

	int len;

	int ciphertext_len;


	/* Create and initialise the context */
	if(!(ctx = EVP_CIPHER_CTX_new())) return -1;

	/* Initialise the encryption operation. */
	if(1 != EVP_EncryptInit_ex(ctx, EVP_aes_256_ccm(), NULL, NULL, NULL))
		return -2;

	/* Setting IV len to 7. Not strictly necessary as this is the default
	 * but shown here for the purposes of this example */
	if(1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_CCM_SET_IVLEN, 7, NULL))
		return -3;

	/* Set tag length */
	EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_CCM_SET_TAG, tag_len, NULL);

	/* Initialise key and IV */
	if(1 != EVP_EncryptInit_ex(ctx, NULL, NULL, key, iv)) return -4;

	/* Provide the total plaintext length
	 */
	if(1 != EVP_EncryptUpdate(ctx, NULL, &len, NULL, plaintext_len))
		return -5;

	/* Provide any AAD data. This can be called zero or one times as
	 * required
	 */
	if(1 != EVP_EncryptUpdate(ctx, NULL, &len, aad, aad_len))
		return -6;

	/* Provide the message to be encrypted, and obtain the encrypted output.
	 * EVP_EncryptUpdate can only be called once for this
	 */
	if(1 != EVP_EncryptUpdate(ctx, ciphertext, &len, plaintext, plaintext_len))
		return -7;
	ciphertext_len = len;

	/* Finalise the encryption. Normally ciphertext bytes may be written at
	 * this stage, but this does not occur in CCM mode
	 */
	if(1 != EVP_EncryptFinal_ex(ctx, ciphertext + len, &len)) return -8;
	ciphertext_len += len;

	/* Get the tag */
	if(1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_CCM_GET_TAG, tag_len, tag))
		return -9;

	/* Clean up */
	EVP_CIPHER_CTX_free(ctx);

	return ciphertext_len;
}


int decryptccm(unsigned const char *ciphertext, int ciphertext_len, unsigned const char *aad,
	int aad_len, unsigned const char *tag, int tag_length, unsigned const char *key, unsigned const char *iv,
	unsigned char *plaintext)
{
	EVP_CIPHER_CTX *ctx;
	int len;
	int plaintext_len;
	int ret;

	/* Create and initialise the context */
	if(!(ctx = EVP_CIPHER_CTX_new())) return -2;

	/* Initialise the decryption operation. */
	if(1 != EVP_DecryptInit_ex(ctx, EVP_aes_256_ccm(), NULL, NULL, NULL))
		return -3;

	/* Setting IV len to 7. Not strictly necessary as this is the default
	 * but shown here for the purposes of this example */
	if(1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_CCM_SET_IVLEN, 7, NULL))
		return -4;

	/* Set expected tag value. */
	if(1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_CCM_SET_TAG, tag_length, tag))
		return -5;

	/* Initialise key and IV */
	if(1 != EVP_DecryptInit_ex(ctx, NULL, NULL, key, iv)) return -6;


	/* Provide the total ciphertext length
	 */
	if(1 != EVP_DecryptUpdate(ctx, NULL, &len, NULL, ciphertext_len))
		return -7;

	/* Provide any AAD data. This can be called zero or more times as
	 * required
	 */
	if(1 != EVP_DecryptUpdate(ctx, NULL, &len, aad, aad_len))
		return -8;

	/* Provide the message to be decrypted, and obtain the plaintext output.
	 * EVP_DecryptUpdate can be called multiple times if necessary
	 */
	ret = EVP_DecryptUpdate(ctx, plaintext, &len, ciphertext, ciphertext_len);

	plaintext_len = len;

	/* Clean up */
	EVP_CIPHER_CTX_free(ctx);

	if(ret > 0)
	{
		/* Success */
		return plaintext_len;
	}
	else
	{
		/* Verify failed */
		return -1;
	}
}
'''

# this largely follows https://gist.github.com/vishvananda/980132c0970f8621bb3c

_FFI.cdef('''
int encryptccm(unsigned const char *plaintext, int plaintext_len, unsigned const char *aad,
	int aad_len, unsigned char *key, unsigned char *iv,
	unsigned char *ciphertext, unsigned char *tag, int tag_len);


int decryptccm(unsigned const char *ciphertext, int ciphertext_len, unsigned const char *aad,
	int aad_len, unsigned const char *tag, int tag_length, unsigned const char *key, unsigned const char *iv,
	unsigned char *plaintext);
        ''')

# for extra_compile_args, see
# https://gist.github.com/vishvananda/980132c0970f8621bb3c for reasons (they
# seem to be marked deprecated on osx)
_C = _FFI.verify(ccm_code, libraries=['crypto'], extra_compile_args=['-Wno-deprecated-declarations'])

def encrypt_ccm(plaintext, aad, key, iv, tag_length):
    assert len(iv) == 7, "IV length mismatch"
    assert len(key) == 32, "Key length mismatch"
    tag_data = _FFI.new("char[%d]" % (tag_length + 1))
    ciphertext_data = _FFI.new("char[%d]" % (len(plaintext) + 1))
    result = _C.encryptccm(plaintext, len(plaintext), aad, len(aad),
            key, iv, ciphertext_data, tag_data, tag_length)
    if result != len(plaintext):
        raise RuntimeError("Encryption backend returned error state: %d"%result)
    assert _FFI.buffer(tag_data)[tag_length] == b'\0', "C function wrote out of bounds."
    assert _FFI.buffer(ciphertext_data)[len(plaintext)] == b'\0', "C function wrote out of bounds."
    tag = _FFI.buffer(tag_data)[:tag_length]
    ciphertext = _FFI.buffer(ciphertext_data)[:len(plaintext)]
    return ciphertext, tag

class InvalidAEAD(Exception): pass

def decrypt_ccm(ciphertext, aad, tag, key, iv):
    assert len(iv) == 7, "IV length mismatch"
    assert len(key) == 32, "Key length mismatch"
    plaintext_data = _FFI.new("char[%d]" % (len(ciphertext) + 1))
    result = _C.decryptccm(ciphertext, len(ciphertext), aad, len(aad),
            tag, len(tag), key, iv, plaintext_data)
    if result == -1:
        raise InvalidAEAD()
    elif result != len(ciphertext):
        raise RuntimeError("Decryption backend returned error state: %d"%result)
    assert _FFI.buffer(plaintext_data)[len(ciphertext)] == b'\0', "C function wrote out of bounds."
    plaintext = _FFI.buffer(plaintext_data)[:len(ciphertext)]
    return plaintext
