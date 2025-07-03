package ranji.dev.location;  // must match with the package name

import javax.crypto.*;
import javax.crypto.spec.IvParameterSpec;
import javax.security.auth.DestroyFailedException;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.security.*;
import java.security.cert.CertificateException;
import java.util.Base64;

public class CryptoLocker{
    public static final String CRYPTOGRAPHIC_ALGORITHM = "AES";
    public static final String ENCRYPTION_MODE = "CBC";
    public static final String PADDING = "PKCS5Padding";
    public final String KEYSTORE_PROVIDER = "AndroidKeyStore";
    private final String KEY_STORE_FILE_NAME = "newKeyStoreFileName.jks";

    public static final String CIPHER_INSTANCE_ARG = CRYPTOGRAPHIC_ALGORITHM + "/" + ENCRYPTION_MODE + "/" + PADDING;
    public byte[] iv = {54, 119, 17, 85, 119, 26, 34, 74, 54, 46, 94, 73, 113, 54, 100, 19};  // random numbers
    IvParameterSpec iv_spec = new IvParameterSpec(iv);


    private void storeKey(SecretKey key, String KEY_ALIAS, String password) throws KeyStoreException, CertificateException, IOException, NoSuchAlgorithmException {
        KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
        char[] pwdArray = password.toCharArray();
        keyStore.load(null, pwdArray);

        KeyStore.ProtectionParameter protectionParam = new KeyStore.PasswordProtection(pwdArray);
        KeyStore.SecretKeyEntry skEntry = new KeyStore.SecretKeyEntry(key);
        keyStore.setEntry(KEY_ALIAS, skEntry, protectionParam);

        // store away the keystore
        try (FileOutputStream fos = new FileOutputStream(KEY_STORE_FILE_NAME)) {
            keyStore.store(fos, pwdArray);
        }
    }

    private SecretKey getStoredKey(String KEY_ALIAS, String password) throws KeyStoreException, UnrecoverableEntryException, NoSuchAlgorithmException, CertificateException, IOException {
        char[] pwdArray = password.toCharArray();
        KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
        KeyStore.ProtectionParameter protectionParam = new KeyStore.PasswordProtection(pwdArray);
        keyStore.load(null, pwdArray);
        try (FileInputStream fis = new FileInputStream(KEY_STORE_FILE_NAME)) {
            keyStore.load(fis, pwdArray);
        } catch (FileNotFoundException e) {
            throw new KeyStoreException("Specified file not found \"{KEY_STORE_FILE_NAME}\"");
        }

        // get my private key
        KeyStore.SecretKeyEntry skEntry = (KeyStore.SecretKeyEntry) keyStore.getEntry(KEY_ALIAS, protectionParam);
        return skEntry.getSecretKey();
    }

    public SecretKey generateNewKey() throws NoSuchAlgorithmException {
        KeyGenerator keyGen = KeyGenerator.getInstance(CRYPTOGRAPHIC_ALGORITHM);
        keyGen.init(256);
        return keyGen.generateKey();
    }

    public void destroyKey(SecretKey key) throws DestroyFailedException {
        key.destroy();
    }

    public SecretKey getKey(String KEY_ALIAS, String password) throws NoSuchAlgorithmException, CertificateException, KeyStoreException, IOException {
        SecretKey key;
        try {
            key = getStoredKey(KEY_ALIAS, password);
            System.out.println("Old key retrieved successfully");
        } catch (KeyStoreException | UnrecoverableEntryException | NoSuchAlgorithmException e) {
//            throw new RuntimeException(e);
            key = generateNewKey();
            storeKey(key, KEY_ALIAS, password);
            System.out.println("New key is generated");
        }
        return key;
    }

    public SecretKey getKey(String KEY_ALIAS, String password, Boolean generateNewKey) throws CertificateException, KeyStoreException, IOException, NoSuchAlgorithmException {
        SecretKey key;
        if (generateNewKey) {
            key = generateNewKey();
            storeKey(key, KEY_ALIAS, password);
            System.out.println("New key is generated with the same key_alias");
        }
        else {
            key = getKey(KEY_ALIAS, password);
        }
        return key;
    }

    public String encryptText(String text, SecretKey key) throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException, IllegalBlockSizeException, BadPaddingException, InvalidAlgorithmParameterException {
        Cipher cipher = Cipher.getInstance(CIPHER_INSTANCE_ARG);
//        System.out.println("iv while encryption -> " + iv_spec.hashCode());
        cipher.init(Cipher.ENCRYPT_MODE, key, iv_spec);
        byte[] cipherText = cipher.doFinal(text.getBytes());
        return Base64.getEncoder().encodeToString(cipherText);
    }

    public String decryptText(String cipherText, SecretKey key) throws NoSuchPaddingException, BadPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException, InvalidAlgorithmParameterException {

        Cipher cipher = Cipher.getInstance(CIPHER_INSTANCE_ARG);
//        System.out.println("iv while decryption -> " + iv_spec.hashCode());
        cipher.init(Cipher.DECRYPT_MODE, key, iv_spec);
        byte[] plainText = cipher.doFinal(Base64.getDecoder().decode(cipherText));
        return new String(plainText);
    }

    public String decryptText(String cipherText, String keyAlias, String password) throws NoSuchPaddingException, BadPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException, CertificateException, KeyStoreException, IOException, InvalidAlgorithmParameterException {
        SecretKey key = getKey(keyAlias, password);
        return decryptText(cipherText, key);
    }


    // TIP IMPORTANT:
    // Below 2 functions works properly so "DO NOT TOUCH IT"
    public static String encrypt(String input, SecretKey key) throws NoSuchPaddingException, NoSuchAlgorithmException, BadPaddingException, IllegalBlockSizeException, InvalidKeyException {
        Cipher cipher = Cipher.getInstance(CIPHER_INSTANCE_ARG);
        cipher.init(Cipher.ENCRYPT_MODE, key);
        byte[] cipherText = cipher.doFinal(input.getBytes());
        return Base64.getEncoder().encodeToString(cipherText);
    }
    public static String decrypt(String cipherText, SecretKey key) throws NoSuchPaddingException, BadPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException {

        Cipher cipher = Cipher.getInstance(CIPHER_INSTANCE_ARG);
        cipher.init(Cipher.DECRYPT_MODE, key);
        byte[] plainText = cipher.doFinal(Base64.getDecoder().decode(cipherText));
        return new String(plainText);
    }
}
