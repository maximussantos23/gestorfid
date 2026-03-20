/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.11-MariaDB, for debian-linux-gnu (aarch64)
--
-- Host: localhost    Database: estoque
-- ------------------------------------------------------
-- Server version	10.11.11-MariaDB-0+deb12u1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `custos_produto`
--

DROP TABLE IF EXISTS `custos_produto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `custos_produto` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nome` varchar(128) DEFAULT NULL,
  `vendidos` int(11) DEFAULT NULL,
  `demanda` decimal(4,2) DEFAULT NULL,
  `estoque` int(11) DEFAULT NULL,
  `termino` date DEFAULT NULL,
  `encomenda` date DEFAULT NULL,
  `preco_lote` decimal(4,2) DEFAULT NULL,
  `preco_armazenamento` decimal(4,2) DEFAULT NULL,
  `dias_entrega` int(11) DEFAULT 0,
  `validade_dias` int(11) DEFAULT 0,
  `Q_pedido` int(11) DEFAULT NULL,
  `Q_final` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `produtos`
--

DROP TABLE IF EXISTS `produtos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `produtos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `epc` varchar(32) NOT NULL,
  `nome` varchar(128) DEFAULT NULL,
  `validade` date DEFAULT NULL,
  `setor` varchar(128) DEFAULT NULL,
  `distribuidor` varchar(128) DEFAULT NULL,
  `data` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `epc` (`epc`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `produtos_excluidos`
--

DROP TABLE IF EXISTS `produtos_excluidos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `produtos_excluidos` (
  `id` int(11) NOT NULL,
  `epc` varchar(32) NOT NULL,
  `nome` varchar(128) DEFAULT NULL,
  `validade` date DEFAULT NULL,
  `setor` varchar(128) DEFAULT NULL,
  `distribuidor` varchar(128) DEFAULT NULL,
  `data` datetime DEFAULT NULL,
  `data_exclusao` datetime DEFAULT current_timestamp(),
  `motivo` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `produtos_vendidos`
--

DROP TABLE IF EXISTS `produtos_vendidos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `produtos_vendidos` (
  `id` int(11) NOT NULL,
  `epc` varchar(32) NOT NULL,
  `nome` varchar(128) DEFAULT NULL,
  `validade` date DEFAULT NULL,
  `setor` varchar(128) DEFAULT NULL,
  `distribuidor` varchar(128) DEFAULT NULL,
  `data` datetime DEFAULT NULL,
  `data_venda` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vencimento`
--

DROP TABLE IF EXISTS `vencimento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `vencimento` (
  `dias` int(11) DEFAULT NULL,
  `senha` varchar(128) DEFAULT NULL,
  `dias_analise` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-20 20:04:23
