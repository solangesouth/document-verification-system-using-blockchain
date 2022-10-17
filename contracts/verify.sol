pragma solidity >=0.7.0 <0.9.0;

contract VerifyDoc {
    struct Certificate {
        string hash;
    }

    address private creator;
    mapping(string => Certificate) certificates;

    constructor() {
        creator = msg.sender;
    }

    modifier onlyOwner {
        require(msg.sender == creator, "Only creator can call this function.");
        _;
    }

    event NewCertificateIssue(string _hash);
    function issueCertificate(string memory _hash) public onlyOwner {
        Certificate memory certificate = Certificate(_hash);
        certificates[_hash] = certificate;
        emit NewCertificateIssue(_hash);
    }

    function getHash(string memory _hash) public view returns (string memory) {
        Certificate storage out = certificates[_hash];
        return (out.hash);
    }
}
